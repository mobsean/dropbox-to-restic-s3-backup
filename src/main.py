"""dropbox-to-restic-s3-backup"""

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
    calculate_content_hash,
)
from restic_backup import ResticBackup
from aws_s3_bucket_manager import move_everything_to_deep_archive_in_s3
from dotenv import load_dotenv

load_dotenv()

MOUNT_FOLDER = os.getenv("MOUNT_FOLDER")
DOWNLOADS_DIR = "Dropbox_Bilder"
DBX_FOLDER = "Kamera-Uploads"

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

    listing = list_folder(dbx, DBX_FOLDER)
    logging.info(f"{len(listing)} files")

    successful_files = download_files(
        download_local_dir=DOWNLOADS_DIR,
        listing=listing,
        dbx=dbx,
        dbx_folder=DBX_FOLDER,
    )

    # logging.info(f"Adding {DOWNLOADS_DIR} to restic backup...")
    # restic = ResticBackup()
    # restic_result = restic.add_to_backup(DOWNLOADS_DIR)
    # if not restic_result:
    #    logging.error("Restic backup failed, aborting further steps")
    #    raise RuntimeError("Restic backup failed, aborting further steps")
    # logging.info("Backup completed successfully!")

    # delete_files_from_dropbox(successful_files, dbx, DBX_FOLDER)
    erledigt_dir = os.path.join(f"{DOWNLOADS_DIR}_erledigt")
    move_successfully_backed_up_files(
        successful_files=successful_files,
        download_local_dir=DOWNLOADS_DIR,
        erledigt_dir=erledigt_dir,
    )

    dbx.close()

    # logging.info("Moving everything to S3 DEEP_ARCHIVE...")
    # move_everything_to_deep_archive_in_s3()
    # logging.info("All operations completed successfully!")

    # copy files from erledigt_dir to MOUNT_FOLDER, this mount is not always available.
    # so we wait until it is ready.
    logging.info(f"Waiting for mount {MOUNT_FOLDER}")
    while not os.path.exists(MOUNT_FOLDER):
        logging.info(f"Mount {MOUNT_FOLDER} not available yet. Waiting 30 seconds...")
        time.sleep(300)

    target_dir = os.path.join(MOUNT_FOLDER, os.path.basename(erledigt_dir))
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

            src_hash = calculate_content_hash(src_path)
            dst_hash = calculate_content_hash(dst_path)
            if src_hash != dst_hash:
                logging.error(
                    "Hash mismatch after copy for {filename}: src={src_hash} dst={dst_hash}"
                )
                raise RuntimeError(
                    f"Hash mismatch for {filename} after copy to {dst_path}"
                )
            logging.info(f"Verified copy for {filename} ({src_hash})")
            os.remove(src_path)
            logging.info(f"Deleted local source file {src_path}")

    logging.info(f"Finished copying erledigt files to {target_dir}")
