"""
Supabase Storage utilities for storing and retrieving generated logbook .docx files.
Replaces s3_utils.py — same interface, different backend.
"""
import logging
import os
from datetime import datetime

from supabase import create_client, Client

logger = logging.getLogger(__name__)

STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "logbooks")


def get_supabase_client() -> Client:
    """Create a Supabase client using the service role key (admin access)."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment."
        )
    return create_client(url, key)


def upload_docx_to_storage(
    docx_bytes: bytes,
    user_id: str,
    entry_number: int,
    submission_date: str,
) -> dict:
    """
    Upload a .docx file to Supabase Storage and return a signed download URL.

    Args:
        docx_bytes:      Raw .docx file bytes
        user_id:         Supabase auth user UUID (used as storage folder)
        entry_number:    Logbook entry number
        submission_date: Submission date string (for logging)

    Returns:
        dict with keys: storage_path, presigned_url, file_size_bytes

    Raises:
        RuntimeError: If upload fails or credentials are missing.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    storage_path = f"{user_id}/entry_{entry_number:02d}_{timestamp}.docx"

    try:
        client = get_supabase_client()

        client.storage.from_(STORAGE_BUCKET).upload(
            path=storage_path,
            file=docx_bytes,
            file_options={
                "content-type": (
                    "application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document"
                )
            },
        )

        logger.info(
            f"Uploaded logbook to supabase://{STORAGE_BUCKET}/{storage_path} "
            f"({len(docx_bytes)} bytes)"
        )

        # Generate signed URL valid for 1 hour
        url_data = client.storage.from_(STORAGE_BUCKET).create_signed_url(
            path=storage_path,
            expires_in=3600,
        )
        presigned_url = url_data.get("signedURL") or url_data.get("signed_url", "")

        return {
            "storage_path": storage_path,
            "presigned_url": presigned_url,
            "file_size_bytes": len(docx_bytes),
        }

    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Supabase storage upload failed: {e}")


def get_signed_url(storage_path: str, expires_in: int = 3600) -> str:
    """Generate a fresh signed URL for an existing storage path."""
    try:
        client = get_supabase_client()
        url_data = client.storage.from_(STORAGE_BUCKET).create_signed_url(
            path=storage_path,
            expires_in=expires_in,
        )
        return url_data.get("signedURL") or url_data.get("signed_url", "")
    except Exception as e:
        logger.warning(f"Could not generate signed URL for {storage_path}: {e}")
        return ""
