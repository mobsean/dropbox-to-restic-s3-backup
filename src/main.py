"""dropbox-to-restic-s3-backup
"""

import contextlib
import hashlib
import logging
import os
import time

import dropbox
from restic_backup import ResticBackup
import requests


def get_access_token():
    """Erzeugt aus dem Refresh Token einen neuen Access Token."""
    DROPBOX_TOKEN_URL = "https://api.dropbox.com/oauth2/token"
    DROPBOX_REFRESH_TOKEN = os.getenv('DROPBOX_REFRESH_TOKEN')
    DROPBOX_CLIENT_ID = os.getenv('DROPBOX_CLIENT_ID')
    DROPBOX_CLIENT_SECRET = os.getenv('DROPBOX_CLIENT_SECRET')

    if not all([DROPBOX_REFRESH_TOKEN, DROPBOX_CLIENT_ID, DROPBOX_CLIENT_SECRET]):
        raise ValueError("Fehlende Dropbox-Umgebungsvariablen")

    data = {
        "grant_type": "refresh_token",
        "refresh_token": DROPBOX_REFRESH_TOKEN,
        "client_id": DROPBOX_CLIENT_ID,
        "client_secret": DROPBOX_CLIENT_SECRET,
    }

    r = requests.post(DROPBOX_TOKEN_URL, data=data, timeout=60)
    r.raise_for_status()
    token = r.json()["access_token"]
    return token


def list_folder(dbx, folder, subfolder):
    """List a folder.

    Return a dict mapping unicode filenames to
    FileMetadata|FolderMetadata entries.
    """
    path = '/%s/%s' % (folder, subfolder.replace(os.path.sep, '/'))
    while '//' in path:
        path = path.replace('//', '/')
    path = path.rstrip('/')
    try:
        with stopwatch('list_folder'):
            res = dbx.files_list_folder(path)
    except dropbox.exceptions.ApiError as err:
        logging.info(f'Folder listing failed for {path} -- assumed empty: {err}')
        return {}
    else:
        rv = {}
        for entry in res.entries:
            rv[entry.name] = entry
        return rv

def download(dbx, folder, subfolder, name):
    """Download a file.

    Return the bytes of the file, or None if it doesn't exist.
    """
    path = '/%s/%s/%s' % (folder, subfolder.replace(os.path.sep, '/'), name)
    while '//' in path:
        path = path.replace('//', '/')
    with stopwatch('download'):
        try:
            md, res = dbx.files_download(path)
        except dropbox.exceptions.HttpError as err:
            logging.info(f'*** HTTP error {err}')
            return None
    data = res.content
    #print(len(data), 'bytes; md:', md)
    return data


@contextlib.contextmanager
def stopwatch(message):
    """Context manager to print how long a block of code took."""
    t0 = time.time()
    try:
        yield
    finally:
        t1 = time.time()
        logging.info(f'Total elapsed time for {message}: {t1 - t0:.3f}')

def calculate_content_hash(file_path):
    """Calculate Dropbox content hash for a file.
    
    Splits file into 4MB blocks, hashes each with SHA-256,
    concatenates the hashes, then hashes the result.
    """
    BLOCK_SIZE = 4 * 1024 * 1024  # 4 MB
    hashes = []
    
    with open(file_path, 'rb') as f:
        while True:
            block = f.read(BLOCK_SIZE)
            if not block:
                break
            block_hash = hashlib.sha256(block).digest()
            hashes.append(block_hash)
    
    concatenated = b''.join(hashes)
    content_hash = hashlib.sha256(concatenated).hexdigest()
    
    return content_hash

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    TOKEN = get_access_token()
    dbx = dropbox.Dropbox(TOKEN)

    downloads_dir = 'Dropbox_Bilder'

    dbx_folder = 'Kamera-Uploads'
    dbx_subfolder = ''
    listing = list_folder(dbx, dbx_folder, dbx_subfolder)
    logging.info(f"{len(listing)} files")

    successful_files = []  # Track successfully downloaded and verified files

    for file_name, metadata in listing.items():
        year_prefix = None
        try:
            year_prefix = int(file_name[:4])
        except (ValueError, IndexError):
            logging.info(f"Skipping {file_name} (kein Jahrespräfix)")
            continue

        if year_prefix < 2025:
            logging.info(f"Skipping {file_name} (Jahr {year_prefix} < 2025)")
            continue

        if not isinstance(metadata, dropbox.files.FileMetadata):
            logging.info(f"Skipping {file_name} (kein FileMetadata)")
            continue

        year_dir = os.path.join(downloads_dir, str(year_prefix))
        os.makedirs(year_dir, exist_ok=True)
        local_path = os.path.join(year_dir, file_name)

        # Check if file already exists locally and if content hash matches
        if os.path.exists(local_path):
            expected_hash = metadata.content_hash
            calculated_hash = calculate_content_hash(local_path)
            if calculated_hash == expected_hash:
                logging.info(f"Hash matches for existing file {file_name}, skip download")
                successful_files.append(file_name)
                continue
            
        res = download(dbx, dbx_folder, dbx_subfolder, file_name)
        with open(local_path, 'wb') as f:
            f.write(res)

        expected_hash = metadata.content_hash
        calculated_hash = calculate_content_hash(local_path)
        
        if calculated_hash != expected_hash:
            raise ValueError(f"Hash mismatch for {file_name}: expected {expected_hash}, got {calculated_hash}")    
        successful_files.append(file_name)

    # Add the year folder to restic backup
    logging.info(f"Adding {downloads_dir} to restic backup...")
    restic = ResticBackup()
    restic.add_to_backup(downloads_dir)
    logging.info("Backup completed successfully!")
    
    # Delete successfully backed up files from Dropbox
    if successful_files:
        logging.info(f"Deleting {len(successful_files)} successfully backed up files from Dropbox...")
        for file_name in successful_files:
            try:
                # Construct path correctly, avoiding double slashes
                path_parts = [dbx_folder]
                if dbx_subfolder:
                    path_parts.append(dbx_subfolder)
                path_parts.append(file_name)
                path = '/' + '/'.join(path_parts)
                dbx.files_delete(path)
                logging.info(f"Deleted {file_name} from Dropbox")
            except dropbox.exceptions.ApiError as err:
                logging.info(f"Error deleting {file_name} from Dropbox: {err}")
        logging.info("File deletion from Dropbox completed!")
    else:
        logging.info("No files to delete from Dropbox")
    # Move successfully backed up files to "erledigt" folder locally
    if successful_files:
        erledigt_dir = os.path.join(downloads_dir, 'erledigt')
        os.makedirs(erledigt_dir, exist_ok=True)
        logging.info(f"Moving {len(successful_files)} successfully backed up files to local 'erledigt' folder...")
        for file_name in successful_files:
            src_path = os.path.join(year_dir, file_name)
            dst_path = os.path.join(erledigt_dir, file_name)
            try:
                os.rename(src_path, dst_path)
                logging.info(f"Moved {file_name} to erledigt folder")
            except OSError as err:
                logging.info(f"Error moving {file_name} to erledigt folder: {err}")
        logging.info("Local file moving completed!")
    
    dbx.close()