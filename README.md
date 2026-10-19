# Undergrad

**Find real opportunities. Keep your search organised.**

Undergrad is a web app for students and recent graduates to discover job, internship, graduate-trainee, and remote-work opportunities in one place. It aggregates listings from job APIs and source-specific scrapers, adds structured tags and eligibility information, and helps users manage their search.

> **Project status:** This repository contains an actively developed project. Some integrations—especially the source-specific scrapers and optional email notifications—may require configuration and live testing before production use.

## Features

- **Job discovery:** Browse listings with pagination and filters for search terms, remote work, work style, job type, category, skills, location, NYSC-related criteria, and degree requirements.
- **Personalised recommendations:** Rank opportunities using a user's onboarding preferences, such as career stage, field, location, and tracks of interest.
- **Listing details and reporting:** View individual listings and report suspicious, closed, or otherwise problematic opportunities.
- **Accounts:** Sign up and log in with email/password; Google Sign-In is supported when configured.
- **Saved jobs and applications:** Save opportunities and maintain an application tracker with statuses, dates, and notes.
- **Profile and resume tools:** Maintain an About/Skills profile, upload or download a resume, and extract text/skills from supported documents.
- **AI-assisted writing:** When a Gemini API key is configured, generate application drafts, job summaries/extractions, and resume-tailoring suggestions. Drafts are prepared for review; the app does not send applications automatically.
- **Listing ingestion:** Fetch and filter opportunities from external job APIs and additional source scrapers, with tagging, deduplication, and expiry handling.
- **Operational support:** Includes request rate limiting, event/error tracking, and optional email alerts for feedback and backend errors.
- **Installable web app:** Includes a web app manifest, icons, and a service worker.

## Tech stack

| Area | Technology |
| --- | --- |
| Frontend | React 18, Vite |
| Backend API | Python, FastAPI, Uvicorn |
| Database | SQLite |
| Authentication | Password hashing, JWT-based sessions in HTTP-only cookies, optional Google Sign-In |
| AI features | Google Gemini API (optional) |
| Resume handling | PDF/DOC/DOCX upload and text extraction |
| Job ingestion | External job APIs and Python scrapers |

## Repository layout

```text
undergrad/
├── backend/
│   ├── main.py                 # FastAPI application and route registration
│   ├── routes/                 # Jobs, auth, profile, saved jobs, applications, etc.
│   ├── requirements.txt        # Python dependencies
│   ├── fetch_apis.py           # Listing ingestion entry point
│   ├── scrape_*.py             # Additional source scrapers
│   ├── init_db.py              # SQLite database initialization
│   └── migrate_*.py            # Database schema migrations
├── data/
│   └── listings.db             # SQLite database path used by the app
└── frontend/
    ├── public/                 # PWA manifest, service worker, icons
    └── src/                    # React application
```

## Requirements

- Python 3.10 or newer is recommended.
- Node.js and npm.
- Git.

## Run locally

Run the backend and frontend in **two separate terminals**. Keep both terminals open while using the app. These commands are for Windows PowerShell; macOS/Linux equivalents are noted below.

### Terminal 1 — backend API

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks environment activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again. On macOS/Linux, use `source .venv/bin/activate`.

Open `backend/.env` and set a unique `JWT_SECRET_KEY`. Generate one with:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the generated value into `JWT_SECRET_KEY`. Keep `.env` private and do not commit it.

**Initialize a new local database** (this creates the schema, but does not restore the old job listings):

```powershell
python init_db.py
python migrate_add_persistence_tables.py
python migrate_add_profile_table.py
python migrate_add_resume_columns.py
python migrate_add_auth.py
```

Run those commands from the `backend` directory. Do not run database initialization against a database containing data you need without first making a backup.

Then start the backend, still in Terminal 1 and still inside `backend`:

```powershell
uvicorn main:app --reload
```

The API is normally at `http://localhost:8000`; its interactive docs are at `http://localhost:8000/docs`. Leave this terminal running.

### Terminal 2 — frontend

Open a **second** terminal, change to the repository root if necessary, and run:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL Vite prints, usually `http://localhost:5173`. Leave this terminal running too. The frontend uses `http://localhost:8000` as its API by default; `VITE_API_URL` can override that.

### Populate the job listings

The current Git commit does **not** include `data/listings.db` or a preloaded set of job listings. A newly initialized database starts empty. To try to fetch listings from the configured public APIs and scrapers, stop neither terminal; open a **third terminal**, then run:

```powershell
cd backend
# Activate the backend virtual environment if this is a new terminal:
.\.venv\Scripts\Activate.ps1
python fetch_apis.py
```

The ingestion script needs internet access, and external APIs or scrapers may fail or change. Check its terminal output and `backend/fetch_apis.log`; successful ingestion should add listings to the local database. This does not recreate the old database or its exact contents.

### 3. Optional integrations

Add only the configuration needed for the features you want to use:

- **Gemini AI:** Set `GEMINI_API_KEY` in `backend/.env`; optionally set `GEMINI_MODEL`. AI-powered features can fall back or become unavailable when the key is missing or the provider request fails.
- **Google Sign-In:** Configure `GOOGLE_CLIENT_ID` in the backend environment and the matching client ID in the frontend's Google Sign-In setup.
- **Email alerts:** Configure `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, and `FEEDBACK_NOTIFY_EMAIL`. Use a Gmail app password, not your regular account password.
- **Remote listing sync:** For a separate scraping machine and deployed backend, configure `SYNC_API_KEY` and `SYNC_TARGET_URL` as described by `backend/.env.example` and `backend/sync_to_remote.py`.
- **Production cookies:** Set `COOKIE_SECURE=true` only when the backend is served behind HTTPS.

Do not commit API keys, passwords, JWT secrets, real resumes, or private user data.

## Listing ingestion

The backend's `fetch_apis.py` coordinates listing collection from supported APIs and the additional Jobberman, MyJobMag, and HotNigerianJobs scrapers. You can inspect the script before running it:

```powershell
cd backend
python fetch_apis.py
```

External sources can change their pages, access rules, and API behaviour. The source-specific scrapers have not been verified against live websites as part of this README, so test them individually and check the resulting listings before relying on them in a scheduled production workflow. Respect each source's terms and crawling rules.

## Tests

The backend includes pytest tests. From the `backend/` directory, install pytest if it is not already available, then run:

```powershell
python -m pytest
```

Run the tests against a test environment; back up any database you care about before running scripts that modify it.

## Security and privacy notes

- Keep `.env` files and all credentials out of version control.
- Resume files and the SQLite database can contain sensitive personal information. Store production user data outside the public repository, and do not use real personal records as committed sample data.
- If sensitive information has already been committed, deleting it in a later commit does not remove it from Git history. Remove it from the repository history where appropriate and rotate any exposed credentials.
- Before public deployment, review CORS settings, HTTPS/cookie configuration, database backup and access controls, upload handling, logging, and all third-party data processing.
- A free-tier AI API may have data-use terms that differ from paid plans. Review the provider's current terms before sending real resumes or other sensitive user information.

## Contributing

1. Create a branch for your change.
2. Keep secrets, databases containing real user records, and uploaded resumes out of commits.
3. Run the relevant tests and verify the frontend build with `npm run build` from `frontend/`.
4. Submit a pull request describing the change and any setup or migration steps.

## License

No license file is currently included in this repository. Unless a license is added, reuse and redistribution are not automatically granted.
