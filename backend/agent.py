"""
Step 6: Agent Orchestration Layer
Single entry point that sequences all functions and returns final docx + summary.

Flow:
  1. Validate inputs
  2. Parse raw notes → structured entries
  3. Detect leave/holiday entries → compact notes
  4. Group entries into work rows (merge consecutive similar work)
  5. Call Claude for Section A (objective + scope)
  6. Call Claude for Section C (reflection)
  7. Build DOCX
  8. Upload to S3
  9. Return download link + generation summary

All steps are timestamped and logged.
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Optional

from functions.parse_notes import parseRawNotes
from functions.group_rows import groupIntoWorkRows
from functions.generate_sections import generateSectionA, generateSectionC
from functions.build_docx import buildDocx
from functions.s3_utils import upload_docx_to_s3

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────
# Input validation
# ──────────────────────────────────────────────────────────────────

REQUIRED_METADATA_FIELDS = [
    "student_name",
    "matric_number",
    "company",
    "supervisor",
    "entry_number",
    "period_start",
    "period_end",
    "submission_date",
]

DATE_FORMAT = "%d/%m/%Y"


def _validate_date(date_str: str, field_name: str) -> datetime:
    """Validate and parse a DD/MM/YYYY date string."""
    try:
        return datetime.strptime(date_str.strip(), DATE_FORMAT)
    except ValueError:
        raise ValueError(
            f"'{field_name}' must be in DD/MM/YYYY format. Got: '{date_str}'"
        )


def validate_inputs(request: dict) -> None:
    """
    Validate all inputs before any API call.
    Raises ValueError with a specific message if anything is missing or malformed.
    """
    metadata = request.get("metadata", {})
    raw_notes = request.get("raw_notes", "")
    internship_objective = request.get("internship_objective", "")

    # Check required metadata fields
    def _is_empty(val) -> bool:
        if val is None:
            return True
        return isinstance(val, str) and not val.strip()

    missing = [f for f in REQUIRED_METADATA_FIELDS if _is_empty(metadata.get(f))]
    if missing:
        raise ValueError(f"Missing required metadata fields: {', '.join(missing)}")

    # Validate date formats
    period_start = _validate_date(str(metadata["period_start"]), "period_start")
    period_end = _validate_date(str(metadata["period_end"]), "period_end")
    _validate_date(str(metadata["submission_date"]), "submission_date")

    # Validate period length
    period_days = (period_end - period_start).days
    if period_days < 0:
        raise ValueError("period_end must be after period_start.")
    if period_days > 14:
        logger.warning(
            f"Period spans {period_days} days, which exceeds the recommended 14-day biweekly period."
        )

    # Validate raw notes
    if not raw_notes or not raw_notes.strip():
        raise ValueError("raw_notes cannot be empty.")

    # Validate internship objective
    if not internship_objective or not internship_objective.strip():
        raise ValueError("internship_objective cannot be empty.")

    # Validate entry number
    try:
        entry_num = int(metadata.get("entry_number", 0))
        if entry_num < 1:
            raise ValueError()
    except (TypeError, ValueError):
        raise ValueError("entry_number must be a positive integer.")


def _log_step(step_name: str, start_time: float) -> float:
    """Log a completed step and return current time."""
    elapsed = round(time.time() - start_time, 2)
    logger.info(f"[{step_name}] completed in {elapsed}s")
    return time.time()


# ──────────────────────────────────────────────────────────────────
# Main orchestration function
# ──────────────────────────────────────────────────────────────────

def orchestrate(request: dict) -> dict:
    """
    Main agent entry point. Processes a full logbook generation request.

    Args:
        request: {
            metadata: {student_name, matric_number, company, supervisor,
                       entry_number, period_start, period_end, submission_date},
            raw_notes: str,
            internship_objective: str,
            challenges: str (optional),
            achievements: str (optional),
            prior_section_a: str (optional, for few-shot),
            prior_section_c: str (optional, for few-shot),
        }

    Returns:
        {
            success: bool,
            section_a: str,
            section_b_rows: list[dict],
            section_c: str,
            s3_info: {presigned_url, s3_key, file_size_bytes},
            summary: str,
            token_usage: {total_tokens, estimated_cost_usd},
            warnings: list[str],
        }
    """
    overall_start = time.time()
    warnings: list[str] = []
    total_tokens = 0
    total_cost = 0.0

    logger.info(
        f"[orchestrate] Starting logbook generation | "
        f"student={request.get('metadata', {}).get('student_name')} | "
        f"entry={request.get('metadata', {}).get('entry_number')}"
    )

    # ── Step 1: Validate all inputs ────────────────────────────────
    t = time.time()
    validate_inputs(request)
    t = _log_step("1. validate_inputs", t)

    metadata = request["metadata"]
    raw_notes = request["raw_notes"].strip()
    internship_objective = request["internship_objective"].strip()
    challenges = request.get("challenges", "")
    achievements = request.get("achievements", "")
    prior_section_a = request.get("prior_section_a", "")
    prior_section_c = request.get("prior_section_c", "")

    # Check period length warning
    period_start = datetime.strptime(str(metadata["period_start"]), DATE_FORMAT)
    period_end = datetime.strptime(str(metadata["period_end"]), DATE_FORMAT)
    period_days = (period_end - period_start).days
    if period_days > 14:
        warnings.append(
            f"Note: This period spans {period_days} days, which exceeds the standard 14-day biweekly period."
        )

    # ── Step 2: Parse raw notes ────────────────────────────────────
    entries = parseRawNotes(raw_notes, default_year=period_end.year)
    t = _log_step("2. parseRawNotes", t)
    logger.info(f"  Parsed {len(entries)} daily entries")

    # ── Step 3: Check for all-leave period ────────────────────────
    all_leave = all(e["is_leave"] for e in entries)
    if all_leave:
        warnings.append(
            "All entries appear to be leave/holiday. Work rows will reflect this."
        )

    # ── Step 4: Group into work rows ───────────────────────────────
    work_rows = groupIntoWorkRows(entries)
    t = _log_step("4. groupIntoWorkRows", t)
    logger.info(f"  Grouped into {len(work_rows)} work rows")

    # ── Step 5: Generate Section A ─────────────────────────────────
    section_a, usage_a = generateSectionA(
        metadata=metadata,
        raw_notes=raw_notes,
        internship_objective=internship_objective,
        prior_section_a=prior_section_a,
    )
    total_tokens += usage_a["total_tokens"]
    total_cost += usage_a["estimated_cost_usd"]
    t = _log_step("5. generateSectionA", t)

    # ── Step 6: Generate Section C ─────────────────────────────────
    section_c, usage_c = generateSectionC(
        metadata=metadata,
        work_rows=work_rows,
        challenges=challenges,
        achievements=achievements,
        prior_section_c=prior_section_c,
    )
    total_tokens += usage_c["total_tokens"]
    total_cost += usage_c["estimated_cost_usd"]
    t = _log_step("6. generateSectionC", t)

    # ── Step 7: Build DOCX ─────────────────────────────────────────
    docx_bytes = buildDocx(
        section_a=section_a,
        work_rows=work_rows,
        section_c=section_c,
        metadata=metadata,
    )
    t = _log_step("7. buildDocx", t)
    logger.info(f"  DOCX size: {len(docx_bytes)} bytes")

    # ── Step 8: Upload to S3 ───────────────────────────────────────
    s3_info = {}
    try:
        s3_info = upload_docx_to_s3(
            docx_bytes=docx_bytes,
            student_name=str(metadata["student_name"]),
            entry_number=int(metadata["entry_number"]),
            submission_date=str(metadata["submission_date"]),
        )
        t = _log_step("8. upload_to_s3", t)
    except RuntimeError as e:
        warnings.append(f"S3 upload failed: {e}. DOCX content is still available.")
        logger.error(f"S3 upload error: {e}")

    # ── Step 9: Build summary ──────────────────────────────────────
    total_elapsed = round(time.time() - overall_start, 2)
    summary = (
        f"Generated Logbook Entry {metadata['entry_number']} for {metadata['student_name']} "
        f"| Period: {metadata['period_start']} – {metadata['period_end']} "
        f"| {len(entries)} daily entries → {len(work_rows)} work rows "
        f"| Tokens used: {total_tokens} (≈${total_cost:.4f}) "
        f"| Total time: {total_elapsed}s"
    )
    logger.info(f"[orchestrate] {summary}")

    return {
        "success": True,
        "section_a": section_a,
        "section_b_rows": work_rows,
        "section_c": section_c,
        "docx_bytes": docx_bytes,  # raw bytes — used by FastAPI to stream response
        "s3_info": s3_info,
        "summary": summary,
        "token_usage": {
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(total_cost, 5),
        },
        "warnings": warnings,
    }
