"""
Step 3 Function 2: groupIntoWorkRows
Groups parsed daily entries into merged table rows for Section B.

Input:  list of DailyEntry dicts [{date, tasks[], is_leave}]
Output: list of WorkRow dicts [{task_description, date_from, date_to}]

Logic:
- Consecutive days with the same task theme are merged
- Leave/holiday entries are formatted as a single compact note
- Multi-day tasks show dateFrom → dateTo span
"""
from datetime import datetime, timedelta


def _tasks_are_similar(tasks_a: list[str], tasks_b: list[str]) -> bool:
    """
    Heuristic: two days are 'similar' if they share a keyword in their task descriptions.
    This keeps the table concise without merging unrelated work.
    """
    keywords_a = set()
    for t in tasks_a:
        keywords_a.update(w.lower() for w in t.split() if len(w) > 4)

    keywords_b = set()
    for t in tasks_b:
        keywords_b.update(w.lower() for w in t.split() if len(w) > 4)

    return bool(keywords_a & keywords_b)


def groupIntoWorkRows(entries: list[dict]) -> list[dict]:
    """
    Convert daily parsed entries into merged work table rows.

    Args:
        entries: Output from parseRawNotes — sorted list of daily entries.

    Returns:
        List of work rows: [{task_description, date_from, date_to, is_leave}]
        date_from and date_to are formatted strings DD/MM/YYYY.

    Rules:
    - Leave entries: combined into a single row noting leave period
    - Consecutive days with overlapping task keywords: merged into one row
    - Otherwise: each day gets its own row
    """
    if not entries:
        return []

    rows = []
    i = 0

    while i < len(entries):
        entry = entries[i]

        # Handle leave/holiday entries
        if entry["is_leave"]:
            # Find consecutive leave days
            j = i + 1
            while j < len(entries) and entries[j]["is_leave"]:
                j += 1

            leave_start = entry["date_str"]
            leave_end = entries[j - 1]["date_str"]

            # Collect leave types
            leave_types = set()
            for k in range(i, j):
                for t in entries[k]["tasks"]:
                    leave_types.add(t.strip().title())

            leave_desc = " / ".join(sorted(leave_types)) if leave_types else "Leave"

            rows.append({
                "task_description": leave_desc,
                "date_from": leave_start,
                "date_to": leave_end,
                "is_leave": True,
                "raw_tasks": [t for e in entries[i:j] for t in e["tasks"]],
            })
            i = j
            continue

        # Handle work entries — try to merge consecutive similar days
        j = i + 1
        merged_tasks = list(entry["tasks"])

        while j < len(entries):
            next_entry = entries[j]
            if next_entry["is_leave"]:
                break

            # Only merge if dates are consecutive (no gaps > 3 days, e.g. weekends)
            day_gap = (next_entry["date"] - entries[j - 1]["date"]).days
            if day_gap > 3:
                break

            if _tasks_are_similar(merged_tasks, next_entry["tasks"]):
                merged_tasks.extend(next_entry["tasks"])
                j += 1
            else:
                break

        # Build description from merged tasks, deduplicated
        seen = set()
        unique_tasks = []
        for t in merged_tasks:
            lower = t.lower().strip()
            if lower not in seen:
                seen.add(lower)
                unique_tasks.append(t.strip())

        task_description = "; ".join(unique_tasks)

        rows.append({
            "task_description": task_description,
            "date_from": entry["date_str"],
            "date_to": entries[j - 1]["date_str"],
            "is_leave": False,
            "raw_tasks": merged_tasks,
        })
        i = j

    return rows
