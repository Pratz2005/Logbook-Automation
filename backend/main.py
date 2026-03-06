"""
FastAPI Backend for NTU Logbook Generator

Endpoints:
  POST /api/auth/register   — Create account (matric + password + profile)
  POST /api/auth/login      — Sign in, receive JWT
  GET  /api/profile         — Get current user profile
  PUT  /api/profile         — Update company / supervisor / objective
  POST /api/generate        — Generate a logbook entry (JWT required)
  GET  /api/history         — List past entries for authenticated user
  GET  /health              — Health check

Rate limiting: max 1 concurrent generate per user, minimum 2s between submits.
"""
import asyncio
import base64
import logging
import os
import time
from collections import defaultdict
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from supabase import create_client, Client

from orchestrator import orchestrate, validate_inputs
from functions.storage_utils import get_signed_url
from functions.build_docx import buildDocx

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
    version="2.0.0",
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

# ── Supabase clients ───────────────────────────────────────────────
# Two separate clients to prevent auth state from polluting DB queries:
#   supabase_admin — auth operations only (sign_up, sign_in, admin calls)
#   supabase_db    — database operations only (table select/insert/update)
#                    never used for auth, so its PostgREST header stays as
#                    the service role key and always bypasses RLS correctly.
def _make_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
    return create_client(url, key)

try:
    supabase_admin: Client = _make_client()
    supabase_db: Client = _make_client()
except RuntimeError as e:
    logger.warning(f"Supabase not configured: {e}. Auth endpoints will fail.")
    supabase_admin = None  # type: ignore
    supabase_db = None  # type: ignore

# ── JWT / Auth helper ──────────────────────────────────────────────
async def get_current_user(request: Request) -> dict:
    """Extract and verify the Supabase JWT from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token.")
    token = auth_header.removeprefix("Bearer ")
    try:
        user_resp = supabase_admin.auth.get_user(token)
        return {"user_id": str(user_resp.user.id), "email": user_resp.user.email}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

# ── Rate limiting ──────────────────────────────────────────────────
_last_request_time: dict[str, float] = defaultdict(float)
_active_requests: dict[str, int] = defaultdict(int)
_rate_limit_lock = asyncio.Lock()
MIN_REQUEST_INTERVAL_SECONDS = 2.0


async def _check_rate_limit(key: str) -> None:
    async with _rate_limit_lock:
        elapsed = time.time() - _last_request_time[key]
        if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
            wait = MIN_REQUEST_INTERVAL_SECONDS - elapsed
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {wait:.1f}s before submitting again.",
            )
        if _active_requests[key] > 0:
            raise HTTPException(
                status_code=429,
                detail="A logbook is already being generated. Please wait.",
            )
        _active_requests[key] += 1
        _last_request_time[key] = time.time()


def _release_rate_limit(key: str) -> None:
    _active_requests[key] = max(0, _active_requests[key] - 1)


# ── Pydantic Models ────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    matric_number: str = Field(..., min_length=4, max_length=20)
    password: str = Field(..., min_length=8, max_length=100)
    student_name: str = Field(..., min_length=1, max_length=100)
    company: str = Field(..., min_length=1, max_length=200)
    supervisor: str = Field(..., min_length=1, max_length=100)


class LoginRequest(BaseModel):
    matric_number: str = Field(..., min_length=1, max_length=20)
    password: str = Field(..., min_length=1, max_length=100)


class UpdateProfileRequest(BaseModel):
    company: Optional[str] = Field(default=None, max_length=200)
    supervisor: Optional[str] = Field(default=None, max_length=100)
    internship_objective: Optional[str] = Field(default=None, max_length=2000)


class StudentMetadata(BaseModel):
    student_name: str = Field(..., min_length=1, max_length=100)
    matric_number: str = Field(..., min_length=1, max_length=20)
    company: str = Field(..., min_length=1, max_length=200)
    supervisor: str = Field(..., min_length=1, max_length=100)
    entry_name: str = Field(..., min_length=1, max_length=100)
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
    storage_info: dict
    summary: str
    token_usage: dict
    warnings: list[str]
    docx_base64: str


# ── Auth Endpoints ─────────────────────────────────────────────────

@app.post("/api/auth/register")
async def register(body: RegisterRequest):
    """
    Create a new user account.
    Uses matric_number@ntu.edu.sg as the Supabase auth email.
    """
    email = f"{body.matric_number}@ntu.edu.sg"
    try:
        auth_resp = supabase_admin.auth.sign_up({
            "email": email,
            "password": body.password,
        })
        if not auth_resp.user:
            raise HTTPException(status_code=400, detail="Registration failed: no user returned.")
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Supabase sign_up failed for {email}: {error_msg}")
        if "already" in error_msg.lower() or "unique" in error_msg.lower():
            raise HTTPException(status_code=409, detail="Matric number already registered.")
        raise HTTPException(status_code=400, detail=f"Registration failed: {error_msg}")

    user_id_str = str(auth_resp.user.id)

    # Auto-confirm email so user can sign in immediately (closed friend-group app)
    try:
        supabase_admin.auth.admin.update_user_by_id(
            user_id_str, {"email_confirm": True}
        )
    except Exception as e:
        logger.warning(f"Could not auto-confirm email for {email}: {e}")

    user_id = user_id_str

    # Create profile record
    supabase_db.table("profiles").insert({
        "id": user_id,
        "matric_number": body.matric_number,
        "student_name": body.student_name,
        "company": body.company,
        "supervisor": body.supervisor,
        "internship_objective": "",
    }).execute()

    # Sign in immediately to return a token
    sign_in_resp = supabase_admin.auth.sign_in_with_password({
        "email": email,
        "password": body.password,
    })

    logger.info(f"New user registered: {body.matric_number} ({body.student_name})")

    return {
        "access_token": sign_in_resp.session.access_token,
        "refresh_token": sign_in_resp.session.refresh_token,
        "user_id": user_id,
        "profile": {
            "matric_number": body.matric_number,
            "student_name": body.student_name,
            "company": body.company,
            "supervisor": body.supervisor,
            "internship_objective": "",
        },
    }


@app.post("/api/auth/login")
async def login(body: LoginRequest):
    """Sign in with matric number and password. Returns JWT access token."""
    email = f"{body.matric_number}@ntu.edu.sg"
    try:
        resp = supabase_admin.auth.sign_in_with_password({
            "email": email,
            "password": body.password,
        })
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid matric number or password.")

    user_id = str(resp.user.id)
    profile_resp = supabase_db.table("profiles").select("*").eq("id", user_id).maybe_single().execute()
    profile = profile_resp.data or {}

    logger.info(f"User logged in: {body.matric_number}")

    return {
        "access_token": resp.session.access_token,
        "user_id": user_id,
        "profile": profile,
    }


# ── Profile Endpoints ──────────────────────────────────────────────

@app.get("/api/profile")
async def get_profile(request: Request):
    """Return the authenticated user's profile."""
    user_info = await get_current_user(request)
    result = supabase_db.table("profiles").select("*").eq("id", user_info["user_id"]).limit(1).execute()
    if not result or not result.data:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return result.data[0]


@app.put("/api/profile")
async def update_profile(request: Request, body: UpdateProfileRequest):
    """Update company, supervisor, or internship objective."""
    user_info = await get_current_user(request)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"success": True}
    supabase_db.table("profiles").update(updates).eq("id", user_info["user_id"]).execute()
    return {"success": True}


# ── Generation Endpoint ────────────────────────────────────────────

@app.post("/api/generate", response_model=GenerateResponse)
async def generate_logbook(request_body: GenerateRequest, request: Request):
    """
    Main generation endpoint. Requires JWT.

    Steps: validate → parse → group → Section A → Section C → DOCX → Storage → DB save
    Rate limited: 1 request per 2 seconds per user, 1 concurrent per user.
    """
    user_info = await get_current_user(request)
    rate_key = user_info["user_id"]

    await _check_rate_limit(rate_key)

    try:
        req_dict = request_body.model_dump()
        req_dict["metadata"] = request_body.metadata.model_dump()
        req_dict["user_id"] = user_info["user_id"]

        logger.info(
            f"[POST /api/generate] user={user_info['user_id']} | "
            f"student={req_dict['metadata']['student_name']} | "
            f"entry={req_dict['metadata']['entry_name']}"
        )

        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, orchestrate, req_dict),
            timeout=120.0,
        )

        # Save entry to Supabase DB
        try:
            supabase_db.table("logbook_entries").insert({
                "user_id": user_info["user_id"],
                "entry_name": req_dict["metadata"]["entry_name"],
                "period_start": req_dict["metadata"]["period_start"],
                "period_end": req_dict["metadata"]["period_end"],
                "submission_date": req_dict["metadata"]["submission_date"],
                "section_a": result["section_a"],
                "section_b_json": result["section_b_rows"],
                "section_c": result["section_c"],
                "storage_path": result.get("storage_info", {}).get("storage_path"),
                "token_usage": result["token_usage"],
                "warnings": result["warnings"],
            }).execute()
        except Exception as db_err:
            err_msg = str(db_err)
            logger.error(f"DB save failed (non-fatal): {err_msg}")
            result["warnings"].append(
                f"Entry could not be saved to history. DB error: {err_msg}"
            )

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
        _release_rate_limit(rate_key)


# ── History Endpoint ───────────────────────────────────────────────

@app.get("/api/history")
async def get_history(request: Request):
    """List past logbook entries for the authenticated user."""
    user_info = await get_current_user(request)

    result = (
        supabase_db.table("logbook_entries")
        .select(
            "id, entry_name, period_start, period_end, submission_date, "
            "section_a, section_c, storage_path, token_usage, created_at"
        )
        .eq("user_id", user_info["user_id"])
        .order("created_at", desc=True)
        .execute()
    )

    entries = []
    for entry in result.data:
        presigned_url = None
        if entry.get("storage_path"):
            presigned_url = get_signed_url(entry["storage_path"])
        entries.append({**entry, "presigned_url": presigned_url})

    return {"entries": entries, "count": len(entries)}


# ── History DOCX Re-download ───────────────────────────────────────

@app.get("/api/history/{entry_id}/download")
async def download_history_entry(entry_id: str, request: Request):
    """
    Rebuild and return the DOCX for a past history entry.

    Regenerates the file on-the-fly from the stored section text and metadata
    so the download always uses the latest buildDocx template (correct header,
    correct formatting) regardless of when the entry was originally generated.
    """
    user_info = await get_current_user(request)

    entry_result = (
        supabase_db.table("logbook_entries")
        .select("*")
        .eq("id", entry_id)
        .eq("user_id", user_info["user_id"])
        .limit(1)
        .execute()
    )
    if not entry_result.data:
        raise HTTPException(status_code=404, detail="Entry not found.")
    entry = entry_result.data[0]

    profile_result = (
        supabase_db.table("profiles")
        .select("student_name, matric_number, company, supervisor")
        .eq("id", user_info["user_id"])
        .limit(1)
        .execute()
    )
    if not profile_result.data:
        raise HTTPException(status_code=404, detail="Profile not found.")
    profile = profile_result.data[0]

    metadata = {
        "student_name": profile["student_name"],
        "matric_number": profile["matric_number"],
        "company":       profile["company"],
        "supervisor":    profile["supervisor"],
        "entry_name":    entry["entry_name"],
        "period_start":  entry["period_start"],
        "period_end":    entry["period_end"],
        "submission_date": entry["submission_date"],
    }

    docx_bytes = buildDocx(
        section_a=entry["section_a"],
        work_rows=entry["section_b_json"],
        section_c=entry["section_c"],
        metadata=metadata,
    )

    safe_name  = profile["student_name"].replace(" ", "_")
    safe_entry = entry["entry_name"].replace(" ", "_")
    filename   = f"Logbook_{safe_name}_{safe_entry}.docx"

    return Response(
        content=docx_bytes,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Health ─────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "ntu-logbook-generator", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
