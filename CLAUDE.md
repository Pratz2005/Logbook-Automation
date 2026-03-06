# NTU Logbook Generator — CLAUDE.md

## Project Purpose

This system transforms raw bullet-point daily work notes into formally formatted NTU (Nanyang Technological University) Industrial Attachment Logbook entries. It:

1. Accepts unstructured daily notes (e.g. "9th Feb - produced demo video, set up GitLab CI/CD")
2. Calls the Claude API (`claude-sonnet-4-6`) to generate formal Section A and Section C prose
3. Builds a `.docx` file matching the NTU biweekly logbook template exactly
4. Uploads the document to AWS S3 and returns a presigned download URL
5. Serves the experience via a clean Next.js single-page frontend

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Next.js Frontend (port 3000)                                   │
│  ┌──────────────────┐ ┌──────────────────┐ ┌────────────────┐  │
│  │  MetadataPanel   │ │  NotesPanel      │ │  PreviewPanel  │  │
│  │  (student info)  │ │  (raw notes +    │ │  (Section A,   │  │
│  │  saved to        │ │   objective +    │ │   B table,     │  │
│  │  localStorage)   │ │   prior entries) │ │   Section C)   │  │
│  └──────────────────┘ └──────────────────┘ └────────────────┘  │
│                       lib/api.ts (fetch + debounce)             │
└───────────────────────────────┬─────────────────────────────────┘
                                │ POST /api/generate
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Backend (port 8000)   main.py                          │
│  Rate limiting: 2s min interval, 1 concurrent per IP           │
└───────────────────────────────┬─────────────────────────────────┘
                                │ orchestrate(request)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  agent.py — Orchestration Layer                                 │
│                                                                 │
│  1. validate_inputs(request)                                    │
│       ↓                                                         │
│  2. parseRawNotes(raw_text)                                     │
│       → [{date, tasks[], is_leave}]                             │
│       ↓                                                         │
│  3. groupIntoWorkRows(entries)                                  │
│       → [{task_description, date_from, date_to, is_leave}]     │
│       ↓                                                         │
│  4. generateSectionA(metadata, raw_notes, objective, prior)     │
│       → Claude API call (streaming) → Section A text           │
│       ↓                                                         │
│  5. generateSectionC(metadata, work_rows, challenges, prior)    │
│       → Claude API call (streaming) → Section C text           │
│       ↓                                                         │
│  6. buildDocx(section_a, work_rows, section_c, metadata)        │
│       → python-docx → .docx bytes                              │
│       ↓                                                         │
│  7. upload_docx_to_s3(bytes, ...)                               │
│       → S3 presigned URL                                        │
│       ↓                                                         │
│  8. Return {section_a, section_b_rows, section_c,              │
│             docx_base64, s3_info, token_usage, warnings}        │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│  AWS S3  (ntu-logbook-docs bucket)                              │
│  Key: logbooks/{StudentName}/entry_{N}_{timestamp}.docx         │
└─────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
logbook/
├── CLAUDE.md                        ← This file
├── .gitignore
│
├── backend/
│   ├── main.py                      ← FastAPI app, routes, rate limiting
│   ├── agent.py                     ← Orchestration layer (entry point)
│   ├── requirements.txt
│   ├── .env.example                 ← Required env vars template
│   │
│   ├── functions/
│   │   ├── parse_notes.py           ← parseRawNotes() — Step 3 Fn 1
│   │   ├── group_rows.py            ← groupIntoWorkRows() — Step 3 Fn 2
│   │   ├── generate_sections.py     ← generateSectionA/C() — Step 3 Fn 3/5
│   │   ├── build_docx.py            ← buildDocx() — Step 3 Fn 6
│   │   └── s3_utils.py              ← S3 upload/list — Step 3 Fn 7
│   │
│   ├── prompts/
│   │   └── templates.py             ← All prompt templates + fragment builders
│   │
│   └── tests/
│       └── test_functions.py        ← 11 independent function tests
│
└── frontend/
    ├── app/
    │   ├── layout.tsx               ← Root layout with metadata
    │   ├── page.tsx                 ← Main page (full orchestration UI)
    │   └── globals.css              ← Design system (CSS vars, typography)
    │
    ├── components/
    │   ├── MetadataPanel.tsx        ← Student info form + localStorage save
    │   ├── NotesPanel.tsx           ← Raw notes + objective + optional fields
    │   ├── PreviewPanel.tsx         ← Section A/B/C preview + download
    │   └── HistoryPanel.tsx         ← Past entries from localStorage
    │
    ├── lib/
    │   └── api.ts                   ← Typed API client + localStorage helpers
    │
    └── .env.local                   ← NEXT_PUBLIC_API_URL
```

---

## Prompt Templates (prompts/templates.py)

### Why XML Tags?

All inputs to Claude are structured with XML tags (`<raw_notes>`, `<metadata>`, `<objective>`, `<prior_entry>`) because:
- Claude performs significantly better with clearly delineated input sections
- XML prevents prompt injection — raw user input cannot escape its tag
- Makes it easy to audit exactly what goes into each API call

### System Prompt Structure

Every system prompt follows this structure:
1. **Role** — "You are an expert academic writer helping an NTU undergraduate…"
2. **Context** — What the NTU logbook is, who reads it
3. **Formatting rules** — No markdown, no bullets, plain prose only
4. **Length constraints** — Specific word counts for each section
5. **What to avoid** — "Do NOT mention leave as an area for improvement"

### Section A Prompt

**System** (`SECTION_A_SYSTEM`):
- Sets up the NTU academic context
- Specifies Section A contains: Objective + Scope of Work
- Length: 120–200 words

**User** (`SECTION_A_USER_TEMPLATE`):
- `<metadata>` — student name, company, period, entry number
- `<objective>` — persistent internship objective (pre-written, reused)
- `<raw_notes>` — the raw unprocessed notes text
- `<prior_entry>` — most recent prior Section A for style matching (few-shot)
- Instruction appended: "Do NOT mention leave as part of the scope"

### Section C Prompt

**System** (`SECTION_C_SYSTEM`):
- Specifies exactly 4 subheadings in order: Key Achievements, Main Challenge Faced, What I Did Well, Areas for Improvement
- Length: 200–280 words total, 40–80 words per subsection
- **Critical rule**: "Do NOT mention leave or public holidays as an area for improvement"

**User** (`SECTION_C_USER_TEMPLATE`):
- `<metadata>` — student + company + period
- `<work_done>` — extracted from Section B rows (work only, no leave)
- `<challenges_noted>` — optional user-provided challenge hint
- `<achievements_noted>` — optional user-provided achievement hint
- `<prior_entry>` — most recent prior Section C for style matching

### Few-Shot Context Engineering

`build_prior_entry_block(prior_section_a, prior_section_c)` wraps prior content in a `<prior_entry>` XML block and appends: *"Match the tone, formality level, and approximate length of the above examples."*

This is always passed when available because:
- Students have a consistent writing style across entries
- Claude will match vocabulary, sentence length, and formality exactly
- Without it, each generation can vary significantly in style

---

## How Agent Orchestration Works (agent.py)

The `orchestrate(request)` function is the single synchronous entry point:

```python
orchestrate(request: dict) -> dict
```

Steps:
1. `validate_inputs()` — all fields checked before any API call
2. `parseRawNotes()` — date regex parsing → `[{date, tasks[], is_leave}]`
3. `groupIntoWorkRows()` — consecutive similar days merged; leave separated
4. `generateSectionA()` — Claude API (streaming, retry ≤ 2x)
5. `generateSectionC()` — Claude API (streaming, retry ≤ 2x)
6. `buildDocx()` — python-docx builds the .docx in memory
7. `upload_docx_to_s3()` — boto3 put_object + presigned URL
8. Returns full result dict including `docx_bytes` (raw) + `warnings[]`

FastAPI runs `orchestrate` in a thread pool executor with a 120s timeout:
```python
result = await asyncio.wait_for(
    loop.run_in_executor(None, orchestrate, req_dict),
    timeout=120.0
)
```

---

## How to Add a New Logbook Entry

1. Fill in the **Metadata** panel (student info auto-fills from localStorage)
2. Update **Period Start** and **Period End** dates
3. Increment **Entry No.**
4. Paste raw daily notes in the **Daily Work Notes** textarea
5. Optionally paste prior Section A/C in the Advanced section
6. Click **Generate** — preview appears on the right
7. Click **Download .docx** to save

The system auto-increments entry number and saves the generated sections as `priorSectionA` / `priorSectionC` state for the next generation.

---

## How to Modify the DOCX Template

Edit `backend/functions/build_docx.py`. Key sections:

- **Page setup**: Lines `section.page_height`, `page_width`, margins
- **Header/Footer**: `section.header` and `section.footer`
- **Info table**: `info_fields` list — add/remove/reorder rows
- **Section A box**: `sec_a_table` — change border style via `_set_table_border()`
- **Section B table**: `col_headers`, `col_widths`, `HEADER_BG` colour constant
- **Section C**: Parsed by matching `SUBHEADINGS` list — add new subheadings here

DOCX colour constants at the top of the file:
```python
HEADER_BG = "D5E8F0"       # Section B header fill
BORDER_COLOUR = "000000"   # Table borders
FOOTER_COLOUR = RGBColor(0x80, 0x80, 0x80)  # Footer text
```

---

## Known Edge Cases and How They Are Handled

| Edge Case | Handling |
|-----------|----------|
| Raw notes with no dates | `parseRawNotes()` raises `ValueError` with clear message |
| Comma-separated tasks on same line | Split on `,` or `;` within same date entry |
| Consecutive leave days | Merged into one leave row in Section B |
| All entries are leave | Warning added to `warnings[]`; Section B shows leave row |
| Period > 14 days | Warning added; generation continues |
| Claude returns empty string | Retry with clarified prompt (max 2 retries) |
| Claude API rate limit / 5xx | Exponential backoff retry (2^attempt seconds) |
| S3 upload fails | Warning added; DOCX bytes still returned in `docx_base64` |
| Missing AWS credentials | `RuntimeError` with instructive message |
| Frontend submission < 2s apart | 429 from backend + debounce in `lib/api.ts` |
| Entry number > 99 | Pydantic `Field(ge=1, le=99)` validation |
| Auth state pollutes DB queries | Use two separate Supabase clients (see below) |
| User profile missing after auth user exists | Cleanup SQL deleted profile; re-insert manually or have user re-register |

---

## Supabase Client Architecture (CRITICAL — do not change)

Two separate clients are initialised at startup in `backend/main.py`:

```python
supabase_admin = _make_client()  # auth operations ONLY
supabase_db    = _make_client()  # DB table operations ONLY
```

**Why this matters:** `supabase-py` auth calls (`sign_up()`, `sign_in_with_password()`) mutate the client's internal session state, which overwrites the PostgREST Authorization header. If the same client is used for both auth and DB, subsequent `table()` calls run with the signed-in user's JWT instead of the service role key — RLS then silently filters out other users' rows, returning empty data with no error.

**Rules:**
- `supabase_admin` — ONLY for: `auth.sign_up()`, `auth.sign_in_with_password()`, `auth.admin.*`, `auth.get_user()`
- `supabase_db` — ONLY for: `table(...).select/insert/update/delete`
- NEVER call `supabase_db.auth.*` — doing so will corrupt its PostgREST state
- NEVER call `supabase_admin.table(...)` — its auth state may be a user's token, not service role

---

## Supabase Configuration Requirements

- **"Confirm email" must be OFF** — users register with fake `@ntu.edu.sg` addresses that don't exist. Leaving this ON causes every registration to send a confirmation email that bounces, which causes Supabase to throttle the project and return "User not allowed" 403 errors on subsequent auth calls.
- **"Allow new users to sign up" must be ON** (Sign In / Providers → Email)
- **Service role key** (not anon key) must be in `SUPABASE_SERVICE_ROLE_KEY` env var — the anon key cannot call admin APIs

---

## Auth Flow Notes

- Registration uses `auth.sign_up()` (not `auth.admin.create_user()`) because the admin create endpoint returns "User not allowed" when Supabase's email bounce throttling is active
- After registration, backend calls `sign_in_with_password()` immediately and returns both `access_token` AND `refresh_token` to the frontend
- Frontend must call `supabase.auth.setSession({ access_token, refresh_token })` with the real refresh token — passing an empty string means the session cannot be renewed and the user gets silently logged out after ~1 hour
- `get_profile` uses `.limit(1)` not `.maybe_single()` — `maybe_single()` returns 406 if duplicate rows exist, which crashes with `AttributeError: 'NoneType' object has no attribute 'data'`

---

## Environment Variables

### Backend (.env or environment)

```bash
ANTHROPIC_API_KEY=sk-ant-...        # Required: Claude API key
AWS_ACCESS_KEY_ID=...               # Required: S3 write access
AWS_SECRET_ACCESS_KEY=...           # Required: S3 write access
AWS_REGION=ap-southeast-1           # Default: ap-southeast-1
S3_BUCKET_NAME=ntu-logbook-docs     # Default: ntu-logbook-docs
FRONTEND_URL=http://localhost:3000  # CORS origin
```

### Frontend (.env.local)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## How to Run Tests

```bash
cd backend
python3 tests/test_functions.py
```

Tests cover (11 total, 0 failures):
1. `parseRawNotes` — basic parsing
2. `parseRawNotes` — leave detection
3. `parseRawNotes` — LB3 comma-separated tasks
4. `parseRawNotes` — empty input error
5. `parseRawNotes` — no dates error
6. `groupIntoWorkRows` — basic grouping
7. `groupIntoWorkRows` — leave row handling
8. `groupIntoWorkRows` — all-leave period
9. `buildDocx` — generates valid .docx bytes
10. Full pipeline mock (no API call)
11. Input validation

## How to Run Locally

```bash
# Terminal 1 — Backend
cd backend
pip install -r requirements.txt
cp .env.example .env  # fill in API keys
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev  # runs on port 3000
```

Visit `http://localhost:3000`.
