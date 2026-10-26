# AIVOA

Decision-support web app for pharma quality teams to investigate deviations and possible root causes.

> **Important:** AI suggestions are drafts. A qualified quality professional must review and approve them. This app does not invent facts and does not make batch-release, recall, or other quality decisions. It is decision support, **not validated GMP software**.

**Current state:** through Milestone 9 (final verification pass) - backend, persistence, investigation CRUD, secure intake, the Groq + LangGraph AI workflow, a connected React + Redux Toolkit UI (dashboard, list, create with report intake/analysis, detail edit/archive/reopen), editable hypotheses/gaps/RCA/CAPA with per-entity audit history, and a printable HTML report export (`GET /api/investigations/{id}/export`). Demo MVP: backend (52) and frontend (16) tests pass; verified end-to-end against PostgreSQL. See `revision.md` for actual commands and results. Decision support only - not validated GMP software.

## Stack

- **Frontend:** React + Redux Toolkit (Vite)
- **Backend:** Python + FastAPI
- **Database:** PostgreSQL
- **AI workflow:** LangGraph + Groq (json_object responses, drafts only)

## Project layout

```
AIVOA/
├── backend/            FastAPI app + Python virtual environment
│   ├── app/            Application code (config, db, health endpoint)
│   ├── .venv/          Virtual environment (created locally)
│   └── requirements.txt
├── frontend/           React + Redux Toolkit app (Vite)
├── .env.example        Environment template (no secrets)
├── revision.md         Change log with actual verification results
└── aivoa.md            Project brief
```

## Prerequisites (Windows)

- Python 3.11+ (`python --version`)
- Node.js 18+ with npm (`node --version`, `npm --version`)
- Docker Desktop (used to run PostgreSQL locally)

All commands below are PowerShell, run from the repository root `C:\Users\hp\Desktop\AIVOA`.

## 1. PostgreSQL (Docker)

Start the database container (first run creates it):

```powershell
docker run -d --name aivoa-postgres `
  -e POSTGRES_USER=aivoa `
  -e POSTGRES_PASSWORD=aivoa-local-dev `
  -e POSTGRES_DB=aivoa `
  -p 5432:5432 `
  -v aivoa_pgdata:/var/lib/postgresql/data `
  postgres:16-alpine
```

If the container already exists, start it instead:

```powershell
docker start aivoa-postgres
```

Stop it when finished: `docker stop aivoa-postgres`

## 2. Environment variables

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set at least `DATABASE_PASSWORD` to match the container password. `.env` is git-ignored; never commit real secrets. Set `GROQ_API_KEY` (and optionally `GROQ_MODEL`, default `openai/gpt-oss-120b`) for AI analysis; without a key `/api/analysis` answers 503 with a clear message.

## 3. Backend (FastAPI)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt   # test-only dependencies
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If PowerShell blocks activation, run once: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

Create the database schema (idempotent `create_all`; safe to re-run):

```powershell
python -m app.init_db
```

The init script only creates tables that do not exist yet; it does not alter existing tables. If a model changes, drop and recreate the database (or the Docker volume) and re-run the script.

Backend health check (in a second terminal):

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Expected: `status = ok`, `database.connected = true`.

## 4. Frontend (React + Redux Toolkit)

In a second terminal, from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Available screens (Milestone 5):

- **Dashboard** — real database counts, no fake statistics.
- **Investigations** — filterable list of saved cases.
- **New investigation** — paste report text or upload PDF/TXT/MD/EML (10 MB limit), run rule-based fact extraction and the AI analysis, review facts/unknowns/gaps/hypotheses/CAPA drafts, then save the case (AI drafts are attached as `proposed` items for human review).
- **Investigation detail** — view, edit (hypotheses, evidence gaps, RCA steps, CAPA actions), save, archive, and reopen; audit history is shown.

The dev server proxies `/api` to `http://127.0.0.1:8000`. To point the frontend at a different API host, set `VITE_API_BASE_URL` in a frontend `.env` file (safe to expose; the Groq key is only used server-side and never reaches the browser).

Frontend tests (mocked network, no backend needed) and production build:

```powershell
npm test
npm run build
```

The backend also exposes report intake endpoints (Milestone 3):

| Endpoint | Payload | Behavior |
| --- | --- | --- |
| `POST /api/reports/intake/text` | JSON `{"text": "..."}` (max 200,000 chars) | Normalizes text and extracts draft facts |
| `POST /api/reports/intake/file` | Multipart `file` field | Same, after extracting text from the document |

Upload rules (treated as untrusted input):

- Supported types: PDF (`.pdf`), plain text (`.txt`), Markdown (`.md`), email (`.eml`); other extensions are rejected with HTTP 415.
- Maximum size: 10 MB; larger files are rejected with HTTP 413.
- PDFs require the `%PDF-` signature; damaged PDFs, scanned/image-only PDFs with no text layer, HTML-only EMLs, and empty files are rejected with HTTP 422 and a clear message. No placeholder text is ever returned for a document that failed extraction.
- Text is normalized (Unicode NFKC, control characters removed, whitespace collapsed) before rule-based fact extraction.
- Extraction extracts only facts explicitly present in the report (batch ID, reported result, specification limit, event date, detection context), each with its source quote; missing fields are listed under `missing`, statements about absent records under `missing_information_statements`, and contradictory values under `conflicts`. Nothing is guessed and nothing is filled in.
- Document content is data only: it is never executed or treated as instructions.
- Output is draft material for review by a qualified quality professional.

### AI analysis (Milestone 4)

`POST /api/analysis` (JSON `{"text": "..."}`) runs a small LangGraph workflow through the Groq API:

1. Validate the report (a rejected report returns 422).
2. Extract explicitly stated facts (with quotes).
3. Identify unknowns, evidence gaps, and conflicts.
4. Suggest possible causes (hypotheses) and investigation prompts.
5. Draft corrective and preventive actions.
6. Validate the merged output with Pydantic and safety checks.

Behavior and guarantees:

- Facts, unknowns, evidence gaps, conflicts, hypotheses, prompts, and recommendations are returned in **separate fields**.
- Every hypothesis must have a rationale plus either supporting evidence or an explicit `evidence_status: "unavailable"`. Hypotheses are always unconfirmed drafts.
- The API never returns batch-release, recall, or disposition decisions; outputs containing such decision fields are rejected (HTTP 502).
- Report content is passed to the model as untrusted data (`<report>` block) with explicit instructions not to follow anything inside it.
- Errors: no/empty `GROQ_API_KEY` → HTTP 503 "GROQ_API_KEY is not configured"; Groq failure or malformed/invalid model output → HTTP 502 with a safe message.
- Model is configured via `GROQ_MODEL` (default `openai/gpt-oss-120b`; older defaults like `llama-3.3-70b-versatile` no longer resolve on the Groq API). List your account's models: `python -c "from groq import Groq; from app.config import settings; [print(m.id) for m in Groq(api_key=settings.groq_api_key).models.list().data]"` (run from `backend/` with the venv active). Automated tests use mocked model responses and never need a live key.

## Health check endpoints

| Check | URL | Meaning |
| --- | --- | --- |
| Backend | http://127.0.0.1:8000/api/health | Backend status + PostgreSQL connectivity |
| Frontend | http://localhost:5173 | UI loads and displays the health panel |
| Proxy | http://localhost:5173/api/health | Frontend → backend integration |

If the backend reports `status = degraded`, PostgreSQL is unreachable: check `docker ps` and the `.env` database values.

## Tests

Backend tests (from `backend/` with the venv active). They automatically create and use an isolated `aivoa_test` database on the same PostgreSQL server:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

## Notes

- Implemented: AI workflow (Groq + LangGraph, drafts only), investigation CRUD with audit history, uploads (PDF/TXT/MD/EML, 10 MB), printable HTML report export, archive/reopen.
- Uploaded reports are treated as untrusted input; file type and size limits (10 MB) are enforced server-side.
- Decision support only: no confirmed root causes, no automatic disposition/release/recall decisions, **not validated GMP software**.

## Investigation report export (Milestone 7)

Open any investigation and use **Export report** to get a printable HTML summary (browser: print or save as PDF).
The report contains the investigation overview, reported facts, cause hypotheses, evidence gaps,
RCA steps (5 Whys / Fishbone), CAPA actions, full audit history, and a review/disclaimer notice.
Endpoint: `GET /api/investigations/{id}/export` (404 when the investigation does not exist).
