import logging
import time
from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import settings
from innotter.exceptions.api_exceptions import S3StorageError

logger = logging.getLogger(__name__)

s3_session = boto3.Session(
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
)

def get_s3():
    """Return an S3 client instance using the configured boto3 session."""
    return s3_session.client("s3")


def generate_page_image_s3_path(page_id: int) -> str:
    """
    Create image_s3_path for a page image.
    """
    file_name = time.time_ns()
    image_s3_path = f"innotter/page_image/{page_id}_{file_name}.webp"
    return image_s3_path


def delete_page_image(bucket: str, image_s3_path: str) -> None:
    """
    Delete a page image from an S3 bucket.
    """
    logger.info(f"Start: deleting page image from s3, bucket={bucket}, key={image_s3_path}")

    try:
        s3 = get_s3()
        s3.delete_object(Bucket=bucket, Key=image_s3_path)

        logger.info(f"Success: page image from s3 was deleted, bucket={bucket}, key={image_s3_path}")

    except ClientError:
        logger.exception(
            "S3 rejected the request",
            extra={"bucket": bucket, "key": image_s3_path}
        )
        raise S3StorageError("The page image is not deleted")


def create_presigned_post_for_page_image(
        bucket: str,
        image_s3_path: str,
        expiration: int =3600
) -> dict[str, Any]:
    """
    Generate a presigned URL to share an S3 object.
    """
    logger.info(f"Start: generating presigned post to the page image upload, bucket={bucket}, key={image_s3_path}")

    if not image_s3_path:
        raise S3StorageError("A path to the page image in the database is not exist.")
    try:
        s3 = get_s3()
        post: dict[str, Any] = s3.generate_presigned_post(
            Bucket=bucket,
            Key=image_s3_path,
            Fields={'Content-Type': 'image/*'},
            Conditions=[
                ['content-length-range', 0, 2097152],
                ['starts-with', '$Content-Type', 'image/']
            ],
            ExpiresIn=expiration
        )

        logger.info(f"Success: presigned post to the page image upload was generated, "
                    f"bucket={bucket}, key={image_s3_path}")

        return post

    except ClientError:
        logger.exception(
            "S3 rejected the request",
            extra={"bucket": bucket, "key": image_s3_path}
        )
        raise S3StorageError("Presigned post is not generated")