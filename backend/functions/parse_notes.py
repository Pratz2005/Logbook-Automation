"""
Step 3 Function 1: parseRawNotes
Parses raw bullet-point daily notes into structured daily entries.

Input:  raw text like "9th feb - produced demo video, set up gitlab..."
Output: list of DailyEntry dicts [{date, tasks[]}]
"""
import re
from datetime import datetime
from typing import Optional


MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

# Patterns to detect date prefixes in notes
DATE_PATTERNS = [
    # "9th feb", "9 feb", "9/2", "09/02/2026", "Feb 9"
    r"^(\d{1,2})(?:st|nd|rd|th)?\s+([a-zA-Z]+)(?:\s+(\d{4}))?\s*[-–—:]\s*",
    r"^([a-zA-Z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s+(\d{4}))?\s*[-–—:]\s*",
    r"^(\d{1,2})[\/\-](\d{1,2})(?:[\/\-](\d{2,4}))?\s*[-–—:]\s*",
]

LEAVE_KEYWORDS = ["leave", "sick leave", "annual leave", "medical leave", "off", "holiday", "public holiday", "rest day"]


def _parse_date_from_match(match_groups: tuple, pattern_idx: int, default_year: int = 2026) -> Optional[datetime]:
    """Extract a datetime from regex match groups based on pattern index."""
    try:
        if pattern_idx == 0:
            day = int(match_groups[0])
            month_str = match_groups[1].lower()
            year = int(match_groups[2]) if match_groups[2] else default_year
            month = MONTH_MAP.get(month_str)
            if not month:
                return None
            return datetime(year, month, day)

        elif pattern_idx == 1:
            month_str = match_groups[0].lower()
            day = int(match_groups[1])
            year = int(match_groups[2]) if match_groups[2] else default_year
            month = MONTH_MAP.get(month_str)
            if not month:
                return None
            return datetime(year, month, day)

        elif pattern_idx == 2:
            day = int(match_groups[0])
            month = int(match_groups[1])
            year_raw = match_groups[2]
            if year_raw:
                year = int(year_raw) if len(year_raw) == 4 else 2000 + int(year_raw)
            else:
                year = default_year
            return datetime(year, month, day)

    except (ValueError, KeyError):
        return None


def _is_leave_entry(text: str) -> bool:
    """Check if a task description is a leave/holiday entry."""
    lower = text.lower()
    return any(kw in lower for kw in LEAVE_KEYWORDS)


def parseRawNotes(raw_text: str, default_year: int = 2026) -> list[dict]:
    """
    Parse raw bullet-point daily notes into structured entries.

    Args:
        raw_text: Multi-line unstructured text with dates and task descriptions.
        default_year: Year to use when not specified in notes.

    Returns:
        List of dicts: [{date: datetime, tasks: [str], is_leave: bool}]

    Raises:
        ValueError: If no parseable dates found in the input.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Raw notes cannot be empty.")

    entries: list[dict] = []
    lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]

    current_date: Optional[datetime] = None
    current_tasks: list[str] = []

    def flush():
        nonlocal current_date, current_tasks
        if current_date and current_tasks:
            is_leave = all(_is_leave_entry(t) for t in current_tasks)
            entries.append({
                "date": current_date,
                "date_str": current_date.strftime("%d/%m/%Y"),
                "tasks": current_tasks[:],
                "is_leave": is_leave,
            })
        current_date = None
        current_tasks = []

    for line in lines:
        # Remove leading bullet symbols
        clean = re.sub(r"^[\-\*\•]\s*", "", line).strip()
        if not clean:
            continue

        parsed_date = None
        remainder = clean

        for idx, pattern in enumerate(DATE_PATTERNS):
            m = re.match(pattern, clean, re.IGNORECASE)
            if m:
                parsed_date = _parse_date_from_match(m.groups(), idx, default_year)
                if parsed_date:
                    remainder = clean[m.end():].strip()
                    break

        if parsed_date:
            flush()
            current_date = parsed_date
            if remainder:
                # Multiple tasks on same line separated by full stops
                tasks = [t.strip() for t in re.split(r"\.", remainder) if t.strip()]
                current_tasks.extend(tasks)
        else:
            # Continuation line — add as task to current date
            if current_date:
                tasks = [t.strip() for t in re.split(r"\.", clean) if t.strip()]
                current_tasks.extend(tasks)
            # If no current date, it may be a header — skip silently

    flush()  # flush last entry

    if not entries:
        raise ValueError(
            "No dated entries could be parsed. "
            "Ensure each entry starts with a date (e.g. '9th Feb -', '9/2 -', 'Feb 9 -')."
        )

    # Sort by date
    entries.sort(key=lambda e: e["date"])
    return entries
