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

Open a terminal in the repository root.

### 1. Set up the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

On macOS/Linux, activate the environment with `source .venv/bin/activate` instead of the PowerShell activation command.

Edit `backend/.env` and set a unique `JWT_SECRET_KEY`. Generate one with:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the generated value into `JWT_SECRET_KEY` in `backend/.env`. Do not commit `.env` or share its contents.

For a fresh local database, initialise the schema from the backend directory:

```powershell
python init_db.py
python migrate_add_persistence_tables.py
python migrate_add_profile_table.py
python migrate_add_resume_columns.py
python migrate_add_auth.py
```

These migration scripts are included in the repository. If you are using an existing database, back it up before running migrations. Do not overwrite a database containing data you need.

Start the API from the `backend/` directory:

```powershell
uvicorn main:app --reload
```

The API will normally be available at http://localhost:8000. FastAPI's interactive API documentation is at http://localhost:8000/docs.

### 2. Set up the frontend

In a second terminal, from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Vite will print the local frontend URL, usually http://localhost:5173.

The frontend uses `VITE_API_URL` when set and otherwise defaults to `http://localhost:8000`. If you set a custom API URL, configure the backend's CORS origins to allow your frontend origin as well.

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
