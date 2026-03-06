"""
Step 4: Independent function tests with mock data.
Run with: cd backend && python -m pytest tests/ -v
Or run standalone: python tests/test_functions.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from functions.parse_notes import parseRawNotes
from functions.group_rows import groupIntoWorkRows
from functions.build_docx import buildDocx


# ─────────────────────────────────────────────────────────────────
# Test data: Actual logbook entries from the project
# ─────────────────────────────────────────────────────────────────

MOCK_NOTES_LB1 = """
12th Jan - Attended onboarding session, met team members, set up dev environment
13th Jan - Completed mandatory HR training modules, read project documentation
14th Jan - Set up GitLab account and explored existing codebase
15th Jan - Attended sprint planning meeting, assigned first tickets
16th Jan - Started working on API endpoint for user authentication module
19th Jan - Continued API development, wrote unit tests for auth module
20th Jan - Code review session with mentor, revised authentication logic
21st Jan - Fixed bugs from code review, updated unit tests
22nd Jan - Integrated auth module with frontend, tested end-to-end
23rd Jan - Wrote technical documentation for completed features
"""

MOCK_NOTES_LB2 = """
26th Jan - Worked on dashboard UI components using React
27th Jan - Implemented data visualization charts for analytics page
28th Jan - Public Holiday
29th Jan - Continued dashboard development, added responsive design
30th Jan - Tested dashboard across different browsers, fixed CSS issues
2nd Feb - Attended client demo preparation meeting
3rd Feb - Polished UI based on senior engineer feedback
4th Feb - Worked on backend API for dashboard data endpoints
5th Feb - Integrated dashboard with backend, fixed API response format
6th Feb - Code review and final testing of dashboard feature
"""

MOCK_NOTES_LB3 = """
9th Feb - Produced demo video for client presentation. set up GitLab CI/CD pipeline
10th Feb - Configured automated testing in CI/CD. fixed pipeline failures
11th Feb - Annual Leave
12th Feb - Worked on database schema optimization
13th Feb - Performance testing of optimized queries. documented findings
"""

MOCK_METADATA = {
    "student_name": "Tan Wei Ming",
    "matric_number": "U2012345B",
    "company": "TechCorp Singapore Pte Ltd",
    "supervisor": "John Chen",
    "entry_number": 3,
    "period_start": "09/02/2026",
    "period_end": "13/02/2026",
    "submission_date": "21/02/2026",
}

MOCK_OBJECTIVE = (
    "The objective of this industrial attachment is to gain practical experience in full-stack "
    "software development within a professional environment. Through this internship, I aim to "
    "apply theoretical knowledge acquired during my studies to real-world projects, develop "
    "industry-standard software engineering practices, and build professional competencies in "
    "collaborative team environments."
)


# ─────────────────────────────────────────────────────────────────
# Test 1: parseRawNotes
# ─────────────────────────────────────────────────────────────────

def test_parse_raw_notes_basic():
    print("\n" + "="*60)
    print("TEST 1: parseRawNotes — basic parsing")
    print("="*60)

    entries = parseRawNotes(MOCK_NOTES_LB1)
    assert len(entries) > 0, "Should parse at least one entry"
    print(f"  Parsed {len(entries)} entries")

    for e in entries[:3]:
        print(f"  {e['date_str']}: {e['tasks'][:2]} (leave={e['is_leave']})")

    assert entries[0]["date"].month == 1, "First entry should be January"
    assert entries[0]["date"].day == 12, "First entry should be 12th"
    print("  PASS: Basic parsing works correctly")


def test_parse_notes_with_leave():
    print("\n" + "="*60)
    print("TEST 1b: parseRawNotes — with leave entries")
    print("="*60)

    entries = parseRawNotes(MOCK_NOTES_LB2)
    leave_entries = [e for e in entries if e["is_leave"]]
    work_entries = [e for e in entries if not e["is_leave"]]

    print(f"  Total entries: {len(entries)}")
    print(f"  Leave entries: {len(leave_entries)}")
    print(f"  Work entries: {len(work_entries)}")

    assert len(leave_entries) >= 1, "Should detect at least one leave entry"
    print("  PASS: Leave detection works correctly")


def test_parse_notes_lb3():
    print("\n" + "="*60)
    print("TEST 1c: parseRawNotes — LB3 (full-stop-separated tasks)")
    print("="*60)

    entries = parseRawNotes(MOCK_NOTES_LB3)
    print(f"  Parsed {len(entries)} entries:")
    for e in entries:
        print(f"    {e['date_str']}: tasks={e['tasks']}, leave={e['is_leave']}")

    # 9th Feb should have 2 tasks (split on full stop)
    feb9 = next((e for e in entries if e["date"].day == 9), None)
    assert feb9 is not None, "Should parse 9th Feb entry"
    assert len(feb9["tasks"]) >= 2, "Should split full-stop-separated tasks"
    print("  PASS: Full-stop-separated tasks parsed correctly")


def test_parse_notes_empty():
    print("\n" + "="*60)
    print("TEST 1d: parseRawNotes — empty input (should raise)")
    print("="*60)
    try:
        parseRawNotes("")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  Correctly raised ValueError: {e}")
    print("  PASS")


def test_parse_notes_no_dates():
    print("\n" + "="*60)
    print("TEST 1e: parseRawNotes — no dates (should raise)")
    print("="*60)
    try:
        parseRawNotes("Did some work today.\nDid more work.")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  Correctly raised ValueError: {e}")
    print("  PASS")


# ─────────────────────────────────────────────────────────────────
# Test 2: groupIntoWorkRows
# ─────────────────────────────────────────────────────────────────

def test_group_work_rows_basic():
    print("\n" + "="*60)
    print("TEST 2: groupIntoWorkRows — basic grouping")
    print("="*60)

    entries = parseRawNotes(MOCK_NOTES_LB1)
    rows = groupIntoWorkRows(entries)

    print(f"  {len(entries)} entries → {len(rows)} work rows")
    for r in rows:
        flag = "[LEAVE]" if r["is_leave"] else ""
        print(f"  {flag} {r['date_from']} – {r['date_to']}: {r['task_description'][:70]}...")

    assert len(rows) <= len(entries), "Should have <= rows as input entries (merging)"
    assert len(rows) > 0, "Should have at least one row"
    print("  PASS: Grouping works correctly")


def test_group_rows_with_leave():
    print("\n" + "="*60)
    print("TEST 2b: groupIntoWorkRows — leave handling")
    print("="*60)

    entries = parseRawNotes(MOCK_NOTES_LB2)
    rows = groupIntoWorkRows(entries)

    leave_rows = [r for r in rows if r["is_leave"]]
    work_rows = [r for r in rows if not r["is_leave"]]

    print(f"  Leave rows: {len(leave_rows)}")
    print(f"  Work rows: {len(work_rows)}")
    for r in leave_rows:
        print(f"    LEAVE: {r['task_description']} ({r['date_from']} – {r['date_to']})")

    assert len(leave_rows) >= 1, "Should have at least one leave row"
    print("  PASS: Leave rows correctly separated")


def test_group_rows_all_leave():
    print("\n" + "="*60)
    print("TEST 2c: groupIntoWorkRows — all leave period")
    print("="*60)

    all_leave_notes = """
28th Jan - Public Holiday
29th Jan - Annual Leave
30th Jan - Annual Leave
"""
    entries = parseRawNotes(all_leave_notes)
    rows = groupIntoWorkRows(entries)
    print(f"  {len(entries)} entries → {len(rows)} rows")
    print(f"  All leave: {all(r['is_leave'] for r in rows)}")
    assert len(rows) >= 1
    print("  PASS: All-leave period handled gracefully")


# ─────────────────────────────────────────────────────────────────
# Test 3: buildDocx
# ─────────────────────────────────────────────────────────────────

MOCK_SECTION_A = (
    "During the third biweekly period of my industrial attachment at TechCorp Singapore, "
    "I focused on enhancing the CI/CD pipeline and contributing to database optimisation efforts. "
    "The scope of work encompassed the production of a client demonstration video, configuration "
    "of GitLab CI/CD automated testing pipelines, and performance analysis of database queries. "
    "These activities aligned with the team's sprint objectives and contributed directly to "
    "improving the reliability and efficiency of the development workflow."
)

MOCK_SECTION_C = """Key Achievements
Successfully configured the GitLab CI/CD pipeline with automated testing, which reduced manual deployment steps and improved the team's overall delivery velocity. The demonstration video produced was well-received by stakeholders during the client presentation.

Main Challenge Faced
The primary challenge encountered was diagnosing and resolving pipeline failures caused by environment-specific configuration discrepancies between the local development environment and the CI/CD server. This required systematic debugging and cross-referencing of build logs.

What I Did Well
I demonstrated strong analytical skills in identifying the root cause of CI/CD failures efficiently. My ability to produce a polished demonstration video while simultaneously managing technical tasks reflected good time management and communication skills.

Areas for Improvement
I recognise that my initial approach to database optimisation lacked systematic benchmarking. In future, I will establish performance baselines before making schema changes to better quantify the impact of optimisations."""


def test_build_docx():
    print("\n" + "="*60)
    print("TEST 3: buildDocx — generates valid .docx bytes")
    print("="*60)

    entries = parseRawNotes(MOCK_NOTES_LB3)
    work_rows = groupIntoWorkRows(entries)

    docx_bytes = buildDocx(
        section_a=MOCK_SECTION_A,
        work_rows=work_rows,
        section_c=MOCK_SECTION_C,
        metadata=MOCK_METADATA,
    )

    assert isinstance(docx_bytes, bytes), "Should return bytes"
    assert len(docx_bytes) > 1000, "DOCX should be > 1KB"

    # Verify it's a valid ZIP (docx is a ZIP)
    assert docx_bytes[:2] == b"PK", "DOCX should start with PK (ZIP magic bytes)"

    # Save for manual inspection
    output_path = "/tmp/test_logbook_output.docx"
    with open(output_path, "wb") as f:
        f.write(docx_bytes)

    print(f"  Generated {len(docx_bytes)} bytes")
    print(f"  Saved to {output_path} for manual inspection")
    print("  PASS: buildDocx generates valid .docx")


# ─────────────────────────────────────────────────────────────────
# Test 4: Full pipeline (without Claude API)
# ─────────────────────────────────────────────────────────────────

def test_full_pipeline_mock():
    print("\n" + "="*60)
    print("TEST 4: Full pipeline with mock Section A/C (no API call)")
    print("="*60)

    entries = parseRawNotes(MOCK_NOTES_LB3)
    work_rows = groupIntoWorkRows(entries)
    docx_bytes = buildDocx(
        section_a=MOCK_SECTION_A,
        work_rows=work_rows,
        section_c=MOCK_SECTION_C,
        metadata=MOCK_METADATA,
    )

    print(f"  Entries: {len(entries)}")
    print(f"  Work rows: {len(work_rows)}")
    print(f"  DOCX size: {len(docx_bytes)} bytes")
    assert len(docx_bytes) > 0
    print("  PASS: Full pipeline works end-to-end")


# ─────────────────────────────────────────────────────────────────
# Test 5: Input validation
# ─────────────────────────────────────────────────────────────────

def test_validation():
    print("\n" + "="*60)
    print("TEST 5: Input validation")
    print("="*60)

    from orchestrator import validate_inputs

    # Missing field
    try:
        validate_inputs({"metadata": {}, "raw_notes": "12 Jan - task", "internship_objective": "obj"})
        assert False, "Should raise on missing fields"
    except ValueError as e:
        print(f"  Missing fields: {e}")

    # Invalid date format
    bad_metadata = {**MOCK_METADATA, "period_start": "2026-01-01"}
    try:
        validate_inputs({"metadata": bad_metadata, "raw_notes": "12 Jan - task", "internship_objective": "obj"})
        assert False, "Should raise on bad date format"
    except ValueError as e:
        print(f"  Bad date format: {e}")

    # Empty notes
    try:
        validate_inputs({"metadata": MOCK_METADATA, "raw_notes": "", "internship_objective": "obj"})
        assert False, "Should raise on empty notes"
    except ValueError as e:
        print(f"  Empty notes: {e}")

    print("  PASS: All validation checks work")


# ─────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_parse_raw_notes_basic,
        test_parse_notes_with_leave,
        test_parse_notes_lb3,
        test_parse_notes_empty,
        test_parse_notes_no_dates,
        test_group_work_rows_basic,
        test_group_rows_with_leave,
        test_group_rows_all_leave,
        test_build_docx,
        test_full_pipeline_mock,
        test_validation,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n  FAILED: {test.__name__}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    sys.exit(0 if failed == 0 else 1)
