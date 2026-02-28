"""
AWS S3 utilities for storing and retrieving generated logbook .docx files.
Generates presigned URLs for secure, time-limited downloads.
"""
import os
import logging
from datetime import datetime

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


def get_s3_client():
    """Create and return an S3 client using environment credentials."""
    return boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION", "ap-southeast-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def upload_docx_to_s3(
    docx_bytes: bytes,
    student_name: str,
    entry_number: int,
    submission_date: str,
) -> dict:
    """
    Upload a .docx file to S3 and return metadata including presigned URL.

    Args:
        docx_bytes:      Raw .docx file bytes
        student_name:    Student name for filename
        entry_number:    Logbook entry number
        submission_date: Submission date string

    Returns:
        dict with keys: s3_key, bucket, presigned_url, file_size_bytes

    Raises:
        RuntimeError: If upload fails or credentials are missing.
    """
    bucket = os.getenv("S3_BUCKET_NAME", "ntu-logbook-docs")

    # Build a clean, predictable S3 key
    clean_name = "".join(c if c.isalnum() else "_" for c in student_name)
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    s3_key = f"logbooks/{clean_name}/entry_{entry_number:02d}_{date_str}.docx"

    try:
        client = get_s3_client()

        client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=docx_bytes,
            ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            Metadata={
                "student_name": student_name,
                "entry_number": str(entry_number),
                "submission_date": submission_date,
                "generated_at": datetime.utcnow().isoformat(),
            },
        )

        logger.info(f"Uploaded logbook to s3://{bucket}/{s3_key} ({len(docx_bytes)} bytes)")

        # Generate presigned URL valid for 1 hour
        presigned_url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": s3_key},
            ExpiresIn=3600,
        )

        return {
            "s3_key": s3_key,
            "bucket": bucket,
            "presigned_url": presigned_url,
            "file_size_bytes": len(docx_bytes),
        }

    except NoCredentialsError:
        raise RuntimeError(
            "AWS credentials not configured. Set AWS_ACCESS_KEY_ID and "
            "AWS_SECRET_ACCESS_KEY environment variables."
        )
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        raise RuntimeError(f"S3 upload failed ({error_code}): {e}")


def list_student_logbooks(student_name: str) -> list[dict]:
    """
    List all logbook files for a given student from S3.

    Returns:
        List of dicts with: s3_key, last_modified, file_size_bytes, presigned_url
    """
    bucket = os.getenv("S3_BUCKET_NAME", "ntu-logbook-docs")
    clean_name = "".join(c if c.isalnum() else "_" for c in student_name)
    prefix = f"logbooks/{clean_name}/"

    try:
        client = get_s3_client()
        paginator = client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

        results = []
        for page in pages:
            for obj in page.get("Contents", []):
                url = client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket, "Key": obj["Key"]},
                    ExpiresIn=3600,
                )
                results.append({
                    "s3_key": obj["Key"],
                    "last_modified": obj["LastModified"].isoformat(),
                    "file_size_bytes": obj["Size"],
                    "presigned_url": url,
                })

        return sorted(results, key=lambda x: x["last_modified"], reverse=True)

    except (ClientError, NoCredentialsError) as e:
        logger.warning(f"Could not list S3 objects: {e}")
        return []
