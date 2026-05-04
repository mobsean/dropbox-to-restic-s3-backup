import os
import logging
import boto3
from dotenv import load_dotenv

load_dotenv()

BUCKETS = [
    bucket.strip() for bucket in os.getenv("buckets", "").split(",") if bucket.strip()
]


def toStandard(client, bucket, key):
    copy_source = {"Bucket": bucket, "Key": key}
    client.copy(
        copy_source,
        bucket,
        key,
        ExtraArgs={"StorageClass": "STANDARD", "MetadataDirective": "COPY"},
    )


def toDeepArchive(client, bucket, key):
    copy_source = {"Bucket": bucket, "Key": key}
    client.copy(
        copy_source,
        bucket,
        key,
        ExtraArgs={"StorageClass": "DEEP_ARCHIVE", "MetadataDirective": "COPY"},
    )


def move_everything_to_deep_archive():
    for bucket in BUCKETS:
        logging.info(f"bucket: {bucket}")

        s3 = boto3.client("s3")
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket)

        counter = 0
        counter_changed = 0
        summe_mb = 0
        for page in pages:
            if "Contents" in page:
                for obj in page["Contents"]:
                    counter = counter + 1
                    if not obj["StorageClass"] == "DEEP_ARCHIVE":
                        if obj["Key"].startswith("data/"):
                            counter_changed = counter_changed + 1
                            mb = round(obj["Size"] / (1024 * 1024))
                            summe_mb = summe_mb + mb
                            logging.info(f"{counter_changed}: {obj['Key']} ({mb} MB)")
                            toDeepArchive(client=s3, bucket=bucket, key=obj["Key"])
            else:
                logging.info(f"Der Bucket '{bucket}' ist leer.")
        logging.info(
            f"Summe Dateien: {counter}, geänderte Dateien: {counter_changed}, geändert: {summe_mb} MB"
        )


if __name__ == "__main__":
    logging.info("Starting to move everything to DEEP_ARCHIVE...")
    move_everything_to_deep_archive()
    logging.info("finished.")
