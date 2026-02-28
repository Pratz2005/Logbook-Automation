"""
FastAPI Backend for NTU Logbook Generator

Endpoints:
  POST /api/generate     — Generate a logbook entry (returns preview + download URL)
  GET  /api/history      — List past logbook entries for a student from S3
  GET  /api/download/:key — Redirect to S3 presigned URL
  POST /api/metadata     — Save/update student metadata (returns JSON for localStorage sync)
  GET  /health           — Health check

Rate limiting: max 1 concurrent request per IP, minimum 2s between submissions.
"""
import asyncio
import base64
import io
import logging
import os
import time
from collections import defaultdict
from typing import Annotated, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from agent import orchestrate, validate_inputs
from functions.s3_utils import list_student_logbooks

load_dotenv()

# ── Logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ────────────────────────────────────────────────────────────
app = FastAPI(
    title="NTU Logbook Generator API",
    version="1.0.0",
    description="Transforms raw daily notes into formatted NTU internship logbook entries.",
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting state ────────────────────────────────────────────
_last_request_time: dict[str, float] = defaultdict(float)
_active_requests: dict[str, int] = defaultdict(int)
_rate_limit_lock = asyncio.Lock()
MIN_REQUEST_INTERVAL_SECONDS = 2.0


async def _check_rate_limit(client_ip: str) -> None:
    """
    Enforce:
    - Minimum 2 seconds between submissions from same IP
    - Max 1 concurrent request per IP (queue others)
    """
    async with _rate_limit_lock:
        last_time = _last_request_time[client_ip]
        elapsed = time.time() - last_time
        if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
            wait = MIN_REQUEST_INTERVAL_SECONDS - elapsed
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {wait:.1f}s before submitting again.",
            )
        if _active_requests[client_ip] > 0:
            raise HTTPException(
                status_code=429,
                detail="A logbook is already being generated. Please wait.",
            )
        _active_requests[client_ip] += 1
        _last_request_time[client_ip] = time.time()


def _release_rate_limit(client_ip: str) -> None:
    _active_requests[client_ip] = max(0, _active_requests[client_ip] - 1)


# ── Pydantic Models ────────────────────────────────────────────────

class StudentMetadata(BaseModel):
    student_name: str = Field(..., min_length=1, max_length=100)
    matric_number: str = Field(..., min_length=1, max_length=20)
    company: str = Field(..., min_length=1, max_length=200)
    supervisor: str = Field(..., min_length=1, max_length=100)
    entry_number: int = Field(..., ge=1, le=99)
    period_start: str = Field(..., pattern=r"^\d{2}/\d{2}/\d{4}$")
    period_end: str = Field(..., pattern=r"^\d{2}/\d{2}/\d{4}$")
    submission_date: str = Field(..., pattern=r"^\d{2}/\d{2}/\d{4}$")


class GenerateRequest(BaseModel):
    metadata: StudentMetadata
    raw_notes: str = Field(..., min_length=10, max_length=10000)
    internship_objective: str = Field(..., min_length=20, max_length=2000)
    challenges: Optional[str] = Field(default="", max_length=1000)
    achievements: Optional[str] = Field(default="", max_length=1000)
    prior_section_a: Optional[str] = Field(default="", max_length=3000)
    prior_section_c: Optional[str] = Field(default="", max_length=3000)


class GenerateResponse(BaseModel):
    success: bool
    section_a: str
    section_b_rows: list[dict]
    section_c: str
    s3_info: dict
    summary: str
    token_usage: dict
    warnings: list[str]
    docx_base64: str  # Base64-encoded .docx for direct download


# ── Endpoints ──────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "ntu-logbook-generator"}


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_logbook(request_body: GenerateRequest, request: Request):
    """
    Main generation endpoint.

    Steps: validate → parse → group → generate Section A → generate Section C → build DOCX → upload S3
    Rate limited: 1 request per 2 seconds per IP, 1 concurrent per IP.
    Claude API timeout: 30 seconds (enforced via streaming).
    """
    client_ip = request.client.host if request.client else "unknown"

    await _check_rate_limit(client_ip)

    try:
        # Convert Pydantic model to dict
        req_dict = request_body.model_dump()
        req_dict["metadata"] = request_body.metadata.model_dump()
        # Convert entry_number to int (it already is, but be explicit)
        req_dict["metadata"]["entry_number"] = int(req_dict["metadata"]["entry_number"])
        # Convert period fields to strings with / format
        for field in ["period_start", "period_end", "submission_date"]:
            req_dict["metadata"][field] = str(req_dict["metadata"][field])

        logger.info(
            f"[POST /api/generate] ip={client_ip} | "
            f"student={req_dict['metadata']['student_name']} | "
            f"entry={req_dict['metadata']['entry_number']}"
        )

        # Run orchestration in thread pool (synchronous IO)
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, orchestrate, req_dict),
            timeout=120.0,  # 2 min total timeout
        )

        # Encode docx as base64 for JSON response
        docx_b64 = base64.b64encode(result.pop("docx_bytes", b"")).decode("utf-8")

        return GenerateResponse(
            **result,
            docx_base64=docx_b64,
        )

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Generation timed out. Please try again.")
    except RuntimeError as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _release_rate_limit(client_ip)


@app.get("/api/history/{student_name}")
async def get_history(student_name: str):
    """List past logbook entries for a student from S3."""
    if not student_name.strip():
        raise HTTPException(status_code=400, detail="student_name is required.")

    try:
        entries = list_student_logbooks(student_name)
        return {"entries": entries, "count": len(entries)}
    except Exception as e:
        logger.error(f"History fetch error: {e}")
        raise HTTPException(status_code=500, detail=f"Could not fetch history: {e}")


@app.get("/api/download")
async def download_docx(key: str):
    """
    Return a docx file from S3 by key.
    Used when the presigned URL needs to be proxied through the backend.
    """
    import boto3
    import os

    try:
        client = boto3.client(
            "s3",
            region_name=os.getenv("AWS_REGION", "ap-southeast-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        bucket = os.getenv("S3_BUCKET_NAME", "ntu-logbook-docs")
        obj = client.get_object(Bucket=bucket, Key=key)
        content = obj["Body"].read()

        filename = key.split("/")[-1]
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
