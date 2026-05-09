"""dropbox-to-restic-s3-backup"""

import hashlib
import logging
import os
import shutil
import time
from datetime import datetime

import dropbox
from py_dropbox import (
    download_files,
    get_access_token,
    list_folder,
    delete_files_from_dropbox,
    move_successfully_backed_up_files,
)
from restic_backup import ResticBackup
from aws_s3_bucket_manager import move_everything_to_deep_archive_in_s3


def calculate_file_hash(file_path: str, algorithm: str = "sha256") -> str:
    """Calculate a file hash for copy verification."""
    hash_obj = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


if __name__ == "__main__":
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(
        logs_dir, f"backup_{datetime.now().strftime('%Y-%m-%d')}.log"
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

    TOKEN = get_access_token()
    dbx = dropbox.Dropbox(TOKEN)

    downloads_dir = "Dropbox_Bilder"

    dbx_folder = "Kamera-Uploads"
    dbx_subfolder = ""
    listing = list_folder(dbx, dbx_folder, dbx_subfolder)
    logging.info(f"{len(listing)} files")

    successful_files = download_files(
        download_local_dir=downloads_dir,
        listing=listing,
        dbx=dbx,
        dbx_folder=dbx_folder,
        dbx_subfolder=dbx_subfolder,
    )

    # logging.info(f"Adding {downloads_dir} to restic backup...")
    # restic = ResticBackup()
    # restic_result = restic.add_to_backup(downloads_dir)
    # if not restic_result:
    #    logging.error("Restic backup failed, aborting further steps")
    #    raise RuntimeError("Restic backup failed, aborting further steps")
    # logging.info("Backup completed successfully!")
    #
    # delete_files_from_dropbox(successful_files, dbx, dbx_folder, dbx_subfolder)
    erledigt_dir = os.path.join(f"{downloads_dir}_erledigt")
    move_successfully_backed_up_files(
        successful_files=successful_files,
        download_local_dir=downloads_dir,
        erledigt_dir=erledigt_dir,
    )
    #
    # dbx.close()
    #
    # logging.info("Moving everything to S3 DEEP_ARCHIVE...")
    # move_everything_to_deep_archive_in_s3()
    # logging.info("All operations completed successfully!")
    #
    # copy files from erledigt_dir to /mnt/mobin, this mount is not always available. so we wait until it is ready.
    mobin_mount = "/mnt/mobin"
    logging.info("Waiting for mount %s", mobin_mount)
    while not os.path.exists(mobin_mount):
        logging.warning(
            "Mount %s not available yet. Waiting 30 seconds...", mobin_mount
        )
        time.sleep(300)

    target_dir = os.path.join(mobin_mount, os.path.basename(erledigt_dir))
    logging.info(f"Copying files from {erledigt_dir} to {target_dir}")
    for root, dirs, files in os.walk(erledigt_dir):
        rel_root = os.path.relpath(root, erledigt_dir)
        dest_root = (
            target_dir if rel_root == "." else os.path.join(target_dir, rel_root)
        )
        os.makedirs(dest_root, exist_ok=True)

        for filename in files:
            src_path = os.path.join(root, filename)
            dst_path = os.path.join(dest_root, filename)
            logging.info(f"Copying {src_path} -> {dst_path}")
            shutil.copy2(src_path, dst_path)

            src_hash = calculate_file_hash(src_path)
            dst_hash = calculate_file_hash(dst_path)
            if src_hash != dst_hash:
                logging.error(
                    "Hash mismatch after copy for %s: src=%s dst=%s",
                    filename,
                    src_hash,
                    dst_hash,
                )
                raise RuntimeError(
                    f"Hash mismatch for {filename} after copy to {dst_path}"
                )
            logging.info("Verified copy for %s (%s)", filename, src_hash)

    logging.info(f"Finished copying erledigt files to {target_dir}")
