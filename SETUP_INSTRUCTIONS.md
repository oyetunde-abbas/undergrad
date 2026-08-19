# Undergrad — Update Package (nav-fix onward)

This zip covers everything from the sticky-nav CSS fix through: real job
tagging, backend persistence (Saved/Applications/Profile), resume upload,
multi-user auth, and the three Phase 2 scrapers (Jobberman, MyJobMag,
HotNigerianJobs). It does **not** include the earlier dashboard-only zips —
if you never applied those, ignore them and just use this one.

---

## 1. Back up first

Before touching anything, copy your current `backend/` and
`frontend/src/App.jsx` + `App.css` somewhere safe. If something goes wrong
you want an easy way back.

Also back up your database:
```
copy data\listings.db data\listings.db.backup
```

---

## 2. What to REPLACE (whole-file swaps)

These files fully replace what you currently have — don't merge, just
overwrite:

- `frontend/src/App.jsx`
- `frontend/src/App.css`
- `frontend/index.html`
- **Your entire `backend/` folder's `.py` files** — copy every `.py` file
  from this zip's `backend/` into your real `backend/` folder, overwriting
  any that already exist. Also copy the `routes/` and `schemas/` folders
  the same way (overwrite existing files, keep any of yours that aren't in
  this zip).

Do **not** copy `data/`, `.env`, or `node_modules`/`venv` — none of those
are in this zip on purpose.

## 3. What's brand new (no conflict, just adds)

These are new files you haven't had before — just drop them in, nothing to
merge:
- `backend/auth_utils.py`, `backend/deps.py`
- `backend/routes/auth.py`, `backend/routes/profile.py`
- `backend/migrate_add_persistence_tables.py`
- `backend/migrate_add_profile_table.py`
- `backend/migrate_add_resume_columns.py`
- `backend/migrate_add_auth.py`
- `backend/scrape_jobberman.py`, `backend/scrape_myjobmag.py`, `backend/scrape_hotnigerianjobs.py`

---

## 4. Install new Python packages

Three new packages are needed (auth + file upload support). From
`backend/`:

```
pip install -r requirements.txt
```

That pulls in everything, including the three new ones: `bcrypt`,
`PyJWT`, `python-multipart`.

**Reminder: `requirements.txt` is UTF-16 encoded** — if you ever hand-edit
it, open and save it as UTF-16, not UTF-8, or Python's installer will choke
on it.

---

## 5. Add `JWT_SECRET_KEY` to your `.env`

Your `.env` already exists on your machine and is gitignored, so it wasn't
touched by this zip. You need to add one new line to it yourself.

Generate a secret:
```
python -c "import secrets; print(secrets.token_hex(32))"
```

Add it to `.env`:
```
JWT_SECRET_KEY=<paste the generated value here>
```

**Important:** once you pick a value, don't change it later — changing it
invalidates every existing login session. The backend will refuse to start
at all if this key is missing.

---

## 6. Run the migration scripts (in this order)

These update your real database's schema. All are safe to re-run if
something goes wrong partway — they check before making changes.

From `backend/`, run each of these once:

```
python migrate_add_persistence_tables.py
python migrate_add_profile_table.py
python migrate_add_resume_columns.py
python migrate_add_auth.py
```

What each one does:
- **persistence_tables** — adds Saved Jobs and Applications tracking tables
- **profile_table** — adds the Profile (About me / Skills) table, pre-filled
  with your existing bio text as a starting point
- **resume_columns** — adds resume-upload tracking to the profile table
- **auth** — adds the `users` table, and reworks Saved/Applications/Profile
  to belong to a specific user account instead of being shared

Optional but recommended — re-run the tagging backfill so your existing
listings get the improved work_style/type/category/skills tags:
```
python backfill_tags.py
```

---

## 7. First run

1. Start the backend as usual (`uvicorn main:app --reload` or however you
   normally run it)
2. Start the frontend as usual (`npm run dev`)
3. Open the app — you'll land on a **Log in / Sign up** screen (this is
   new). Since this is the very first account created on your database,
   signing up will automatically attach your existing About/Skills profile
   data to that new account — nothing gets lost.
4. From there the app works as before, plus: Saved jobs and Applications
   now persist for real, Profile has a working resume upload, and you're
   logged in with a real account.

---

## 8. Trying the new job scrapers (optional, not required to use the app)

`scrape_jobberman.py`, `scrape_myjobmag.py`, and `scrape_hotnigerianjobs.py`
are new and have **not been tested against the live internet** — they were
built by inspecting real page content through a tool that could reach
those sites, but the actual HTTP requests were never run. Run each one by
itself first and check a few resulting listings before trusting them:

```
python scrape_jobberman.py
python scrape_myjobmag.py
python scrape_hotnigerianjobs.py
```

Two of the three (`myjobmag.com`, `hotnigerianjobs.com`) also haven't had
their `robots.txt` confirmed — worth a quick check at
`myjobmag.com/robots.txt` and `hotnigerianjobs.com/robots.txt` before
running these at any real frequency.

Once you're happy they're working, they're already wired into
`fetch_apis.py`'s main run — no extra step needed to include them in your
regular fetch cycle.

---

## Quick troubleshooting

- **Backend won't start, mentions JWT_SECRET_KEY** → you missed step 5
- **"no such table" errors** → you missed running the migration scripts in step 6
- **Login screen never goes away after signing up** → check the browser console for a failed request to `/auth/signup`; usually means the backend isn't running or CORS is blocking it
- **requirements.txt install fails with an encoding error** → you or your editor re-saved it as UTF-8; re-copy the one from this zip
