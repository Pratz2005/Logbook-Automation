"""
Step 3 Functions 3, 4 & 5: generateSectionA, generateSectionB, generateSectionC
Call Claude API to transform raw work data into formal logbook prose and table rows.

Uses claude-sonnet-4-6 with streaming for reliability.
Includes retry logic (max 2 retries) with clarified prompts on failure.
Logs all API calls with token usage.
"""
import json
import logging
import time
from typing import Optional

import anthropic

from prompts.templates import (
    SECTION_A_SYSTEM,
    SECTION_A_USER_TEMPLATE,
    SECTION_B_SYSTEM,
    SECTION_B_USER_TEMPLATE,
    SECTION_C_SYSTEM,
    SECTION_C_USER_TEMPLATE,
    build_prior_entry_block,
)

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_RETRIES = 2
TIMEOUT_SECONDS = 30


def _call_claude(
    system: str,
    user_message: str,
    max_tokens: int = 1024,
    retry_count: int = 0,
) -> tuple[str, dict]:
    """
    Make a Claude API call with streaming and retry logic.

    Returns:
        (text_output, usage_stats)

    Raises:
        RuntimeError: After max retries exceeded or unrecoverable error.
    """
    client = anthropic.Anthropic()

    log_prefix = f"[Claude API call, retry={retry_count}]"
    logger.info(f"{log_prefix} model={MODEL}, max_tokens={max_tokens}")
    logger.debug(f"{log_prefix} USER PROMPT:\n{user_message}")

    start_time = time.time()

    try:
        result_text = ""
        usage = {}

        with client.messages.stream(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                result_text += text

            final_msg = stream.get_final_message()
            usage = {
                "input_tokens": final_msg.usage.input_tokens,
                "output_tokens": final_msg.usage.output_tokens,
                "total_tokens": final_msg.usage.input_tokens + final_msg.usage.output_tokens,
                "estimated_cost_usd": round(
                    (final_msg.usage.input_tokens * 3.0 + final_msg.usage.output_tokens * 15.0) / 1_000_000, 5
                ),
            }

        elapsed = round(time.time() - start_time, 2)
        logger.info(
            f"{log_prefix} DONE in {elapsed}s | "
            f"input={usage['input_tokens']} output={usage['output_tokens']} "
            f"cost≈${usage['estimated_cost_usd']}"
        )

        if not result_text.strip():
            raise ValueError("Claude returned empty response.")

        return result_text.strip(), usage

    except (anthropic.RateLimitError, anthropic.APIStatusError) as e:
        logger.warning(f"{log_prefix} API error: {e}")
        if retry_count < MAX_RETRIES:
            wait = 2 ** retry_count
            logger.info(f"{log_prefix} Retrying in {wait}s...")
            time.sleep(wait)
            return _call_claude(system, user_message, max_tokens, retry_count + 1)
        raise RuntimeError(f"Claude API failed after {MAX_RETRIES} retries: {e}")

    except ValueError as e:
        if retry_count < MAX_RETRIES:
            # Clarify prompt on empty response
            clarified_message = user_message + "\n\nIMPORTANT: You MUST produce a non-empty response."
            logger.info(f"{log_prefix} Empty response — retrying with clarified prompt.")
            return _call_claude(system, clarified_message, max_tokens, retry_count + 1)
        raise RuntimeError(f"Claude returned empty response after {MAX_RETRIES} retries.")


def generateSectionA(
    metadata: dict,
    raw_notes: str,
    internship_objective: str,
    prior_section_a: str = "",
) -> tuple[str, dict]:
    """
    Generate Section A (Objective + Scope of Work) via Claude API.

    Args:
        metadata: Student metadata dict with keys: student_name, matric_number,
                  company, supervisor, entry_number, period_start, period_end, submission_date
        raw_notes: The raw unparsed notes text for context
        internship_objective: Persistent internship objective statement
        prior_section_a: Most recent prior Section A for few-shot style matching

    Returns:
        (section_a_text, usage_stats)
    """
    prior_block = build_prior_entry_block(prior_section_a=prior_section_a)

    user_message = SECTION_A_USER_TEMPLATE.format(
        student_name=metadata.get("student_name", ""),
        matric_number=metadata.get("matric_number", ""),
        company=metadata.get("company", ""),
        supervisor=metadata.get("supervisor", ""),
        entry_name=metadata.get("entry_name", ""),
        period_start=metadata.get("period_start", ""),
        period_end=metadata.get("period_end", ""),
        submission_date=metadata.get("submission_date", ""),
        internship_objective=internship_objective,
        raw_notes=raw_notes,
        prior_entry_block=prior_block,
    )

    return _call_claude(SECTION_A_SYSTEM, user_message, max_tokens=512)


def generateSectionC(
    metadata: dict,
    work_rows: list[dict],
    challenges: str = "",
    achievements: str = "",
    prior_section_c: str = "",
) -> tuple[str, dict]:
    """
    Generate Section C (Reflection) via Claude API.

    Args:
        metadata: Student metadata dict
        work_rows: Output from groupIntoWorkRows — list of work table rows
        challenges: Optional explicit challenge notes from user
        achievements: Optional explicit achievement notes from user
        prior_section_c: Most recent prior Section C for few-shot style matching

    Returns:
        (section_c_text, usage_stats)
    """
    # Build work summary from rows (exclude leave entries)
    work_items = [
        f"- {row['task_description']} ({row['date_from']} to {row['date_to']})"
        for row in work_rows
        if not row.get("is_leave")
    ]
    work_summary = "\n".join(work_items) if work_items else "General project tasks."

    prior_block = build_prior_entry_block(prior_section_c=prior_section_c)

    user_message = SECTION_C_USER_TEMPLATE.format(
        student_name=metadata.get("student_name", ""),
        company=metadata.get("company", ""),
        entry_name=metadata.get("entry_name", ""),
        period_start=metadata.get("period_start", ""),
        period_end=metadata.get("period_end", ""),
        work_summary=work_summary,
        challenges=challenges or "Not specified by student.",
        achievements=achievements or "Not specified by student.",
        prior_entry_block=prior_block,
    )

    return _call_claude(SECTION_C_SYSTEM, user_message, max_tokens=600)


def _parse_section_b_json(raw: str) -> list[dict]:
    """
    Extract and validate the JSON array from Claude's Section B response.
    Strips markdown code fences if present.

    Raises:
        ValueError / json.JSONDecodeError: if the response is not a valid row list.
    """
    text = raw.strip()

    # Strip markdown code fences Claude might wrap around JSON
    if text.startswith("```"):
        parts = text.split("```")
        # parts[1] is the content between first pair of fences
        text = parts[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    rows = json.loads(text)
    if not isinstance(rows, list):
        raise ValueError(f"Expected JSON array, got {type(rows).__name__}")

    result = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"Row is not a dict: {row!r}")
        result.append({
            "task_description": str(row["task_description"]),
            "date_from": str(row["date_from"]),
            "date_to": str(row["date_to"]),
            "is_leave": bool(row.get("is_leave", False)),
            "raw_tasks": [],  # not tracked when using Claude grouping
        })

    return result


def generateSectionB(
    entries: list[dict],
    metadata: dict,
) -> tuple[list[dict], dict]:
    """
    Use Claude to semantically group daily entries into Section B work rows.

    Claude decides which consecutive days to merge based on the similarity of the
    work described — handling typos, paraphrasing, and related tasks correctly.

    Falls back to heuristic groupIntoWorkRows() if Claude returns unparseable JSON.

    Args:
        entries:  Output from parseRawNotes — sorted list of daily entries.
        metadata: Student metadata dict (used for period_start / period_end context).

    Returns:
        (work_rows, usage_stats)
        work_rows: [{task_description, date_from, date_to, is_leave, raw_tasks}]
    """
    if not entries:
        return [], {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "estimated_cost_usd": 0.0}

    # Format each entry as a readable line for the prompt
    lines = []
    for e in entries:
        tag = "[LEAVE]" if e["is_leave"] else "[WORK]"
        tasks_str = "; ".join(e["tasks"]) if e["tasks"] else "No tasks recorded"
        lines.append(f"{e['date_str']} {tag}: {tasks_str}")
    entries_text = "\n".join(lines)

    user_message = SECTION_B_USER_TEMPLATE.format(
        entries_text=entries_text,
        period_start=metadata.get("period_start", ""),
        period_end=metadata.get("period_end", ""),
    )

    raw_response, usage = _call_claude(SECTION_B_SYSTEM, user_message, max_tokens=1024)

    try:
        rows = _parse_section_b_json(raw_response)
        logger.info(f"[generateSectionB] Claude produced {len(rows)} work rows")
        return rows, usage
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        logger.warning(
            f"[generateSectionB] JSON parse failed ({exc}) — falling back to heuristic grouping"
        )
        # Lazy import to avoid circular dependency
        from functions.group_rows import groupIntoWorkRows
        fallback_rows = groupIntoWorkRows(entries)
        return fallback_rows, usage
