import sqlite3
import json
from pathlib import Path

import eligibility
import scam_guard
from expiry import (
    MISSED_SCRAPES_TO_CLOSE, REPORTS_TO_HIDE, decorate, dedupe_key, default_expiry,
    fmt, parse_deadline, parse_ts, utcnow,
)


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "data" / "listings.db"


_wal_done = set()


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    # Switching to WAL needs a brief exclusive lock. Do it once per database file, and
    # never let a concurrent first request fail because another one is mid-switch.
    key = str(DB_PATH)
    if key not in _wal_done:
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            _wal_done.add(key)
        except sqlite3.OperationalError:
            pass  # try again on the next connection
    return conn


# Feed visibility: only live, in-date listings, and never a cross-source duplicate
# whose original is still live. Closed/expired rows stay in the table (Saved and
# Applications still need them) — they just don't appear in Explore.
_LIVE = "status = 'active' AND (expires_at IS NULL OR expires_at > datetime('now'))"
FEED_FILTER = (
    f"{_LIVE} AND (duplicate_of IS NULL OR duplicate_of NOT IN "
    f"(SELECT id FROM listings WHERE {_LIVE}))"
)


def insert_listing(listing, from_sync=False):
    """
    Upserts a listing on apply_url.

    Normal scrape: stamps first/last seen, computes expires_at (real parsed
    deadline, else 30 days — 21 for internships — after first seen), resets the
    missed-scrape counter, and re-opens a listing that had been closed.

    from_sync=True (the /admin/sync-listings endpoint): the scraping machine is
    the source of truth for lifecycle fields, so its timestamps/status are kept
    instead of being re-stamped with "now" — otherwise every sync would make
    every closed listing look freshly seen. Listings hidden by user reports
    (under_review) are never overwritten by a sync.
    """
    conn = get_conn()
    try:
        now = utcnow()
        now_s = fmt(now)
        ltype = listing.get("type", "Internship")
        parsed = parse_deadline(listing.get("deadline"), now=now)

        if from_sync:
            first_seen = listing.get("first_seen_at") or now_s
            last_seen = listing.get("last_seen_at") or now_s
            expires = (
                listing.get("expires_at") or parsed
                or default_expiry(parse_ts(first_seen) or now, ltype)
            )
            expires_update = listing.get("expires_at") or parsed
            status = listing.get("status") or "active"
        else:
            first_seen = last_seen = now_s
            expires = parsed or default_expiry(now, ltype)
            expires_update = parsed
            # a listing that arrives already past its deadline is born expired
            status = "expired" if expires <= now_s else "active"

        # Scam screen + Nigerian eligibility signals, from the listing's own text.
        flag_reason = scam_guard.check(f"{listing['title']}\n{listing.get('summary') or ''}")
        elig = eligibility.analyse(listing["title"], listing.get("summary"))
        if flag_reason and status == "active":
            status = "under_review"

        params = {
            "title": listing["title"],
            "company": listing.get("company"),
            "summary": listing.get("summary"),
            "apply_url": listing["apply_url"],
            "deadline": listing.get("deadline"),
            "location": listing.get("location"),
            "remote": listing.get("remote", 0),
            "work_style": listing.get("work_style", ""),
            "type": ltype,
            "category": listing.get("category", "Technology"),
            "skills": listing.get("skills", ""),
            "experience_level": listing.get("experience_level", "Entry Level"),
            "source": listing.get("source", "api"),
            "content_hash": listing.get("content_hash"),
            "status": status,
            "needs_manual_review": listing.get("needs_manual_review", 0),
            "first_seen_at": first_seen,
            "last_seen_at": last_seen,
            "expires_at": expires,
            "expires_update": expires_update,
            "dedupe_key": dedupe_key(listing["title"], listing.get("company")),
            "from_sync": 1 if from_sync else 0,
            "flagged": 1 if flag_reason else 0,
            "flag_reason": flag_reason,
            "nysc_req": elig["nysc_req"],
            "min_degree": elig["min_degree"],
        }

        conn.execute("""
        INSERT INTO listings(
            title, company, summary, apply_url, deadline, location, remote,
            work_style, type, category, skills, experience_level, source,
            content_hash, status, needs_manual_review,
            first_seen_at, last_seen_at, expires_at, dedupe_key, missed_scrapes,
            flag_reason, nysc_req, min_degree, eligibility_checked
        )
        VALUES(
            :title, :company, :summary, :apply_url, :deadline, :location, :remote,
            :work_style, :type, :category, :skills, :experience_level, :source,
            :content_hash, :status, :needs_manual_review,
            :first_seen_at, :last_seen_at, :expires_at, :dedupe_key, 0,
            :flag_reason, :nysc_req, :min_degree, 1
        )
        ON CONFLICT(apply_url) DO UPDATE SET
            title=excluded.title,
            company=excluded.company,
            summary=excluded.summary,
            deadline=excluded.deadline,
            location=excluded.location,
            remote=excluded.remote,
            work_style=excluded.work_style,
            type=excluded.type,
            category=excluded.category,
            skills=excluded.skills,
            experience_level=excluded.experience_level,
            dedupe_key=excluded.dedupe_key,
            last_seen_at=excluded.last_seen_at,
            missed_scrapes=0,
            nysc_req=:nysc_req,
            min_degree=:min_degree,
            eligibility_checked=1,
            flag_reason=CASE WHEN :flagged = 1 THEN :flag_reason ELSE listings.flag_reason END,
            expires_at=COALESCE(:expires_update, listings.expires_at),
            status=CASE
                WHEN listings.status = 'under_review' THEN 'under_review'
                WHEN :flagged = 1 AND COALESCE(listings.scam_cleared, 0) = 0 THEN 'under_review'
                WHEN :from_sync = 1 THEN :status
                WHEN COALESCE(:expires_update, listings.expires_at) <= datetime('now') THEN 'expired'
                ELSE 'active'
            END
        """, params)

        # re-opened listings are no longer "closed"
        conn.execute(
            "UPDATE listings SET closed_at = NULL WHERE apply_url = ? AND status = 'active' AND closed_at IS NOT NULL",
            (listing["apply_url"],),
        )
        # cross-source duplicate: keep the oldest live copy, hide newer ones
        if params["dedupe_key"]:
            conn.execute(
                """
                UPDATE listings SET duplicate_of = (
                    SELECT MIN(l2.id) FROM listings l2
                    WHERE l2.dedupe_key = listings.dedupe_key
                      AND l2.id < listings.id AND l2.status = 'active'
                )
                WHERE apply_url = ? AND duplicate_of IS NULL
                """,
                (listing["apply_url"],),
            )
        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        conn.close()



_NYSC_VALUES = {"accepted": "nysc_ok", "post": "post_nysc", "siwes": "siwes"}
_DEGREE_RANK_SQL = (
    "(CASE min_degree WHEN 'first' THEN 5 WHEN '2:1' THEN 4 WHEN '2:2' THEN 3 "
    "WHEN 'hnd' THEN 2 WHEN 'ond' THEN 1 ELSE 0 END)"
)


def _eligibility_filters(nysc, my_degree):
    """
    nysc: accepted | post | siwes   -> only listings whose text says so.
    my_degree: first | 2:1 | 2:2 | hnd | ond -> hides roles that REQUIRE a higher
    class than yours. Listings that state no requirement stay visible (unknown is
    not "no") so a missing phrase never hides a job you could apply for.
    """
    sql, params = "", []
    if nysc in _NYSC_VALUES:
        sql += " AND nysc_req = ?"
        params.append(_NYSC_VALUES[nysc])
    if my_degree in eligibility.TIER:
        sql += f" AND {_DEGREE_RANK_SQL} <= ?"
        params.append(eligibility.TIER[my_degree])
    return sql, params


def get_jobs(
    page=1,
    limit=20,
    search="",
    remote=None,
    work_style="",
    job_type="",
    category="",
    skill="",
    location="",
    sort="newest",
    nysc="",
    my_degree=""
):

    offset=(page-1)*limit


    query="""
    SELECT *
    FROM listings
    WHERE """ + FEED_FILTER + """
    """

    params=[]


    if search:

        query += """
        AND(
            title LIKE ?
            OR company LIKE ?
            OR summary LIKE ?
            OR skills LIKE ?
        )
        """

        params.extend([
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ])


    if remote is not None:

        query+=" AND remote=?"
        params.append(remote)


    if work_style:

        query+=" AND work_style=?"
        params.append(work_style)


    if job_type:

        query+=" AND type=?"
        params.append(job_type)


    if category:

        query+=" AND category=?"
        params.append(category)


    if skill:

        query+=" AND skills LIKE ?"
        params.append(f"%{skill}%")


    if location:

        query+=" AND location LIKE ?"
        params.append(f"%{location}%")


    extra_sql, extra_params = _eligibility_filters(nysc, my_degree)
    query += extra_sql
    params.extend(extra_params)


    if sort=="oldest":

        query+=" ORDER BY created_at ASC"

    else:

        query+=" ORDER BY created_at DESC"



    query+=" LIMIT ? OFFSET ?"

    params.extend([
        limit,
        offset
    ])


    conn=get_conn()

    rows=conn.execute(
        query,
        params
    ).fetchall()

    conn.close()


    return [
        decorate(dict(row))
        for row in rows
    ]




def count_jobs(
    search="",
    remote=None,
    work_style="",
    job_type="",
    category="",
    skill="",
    location="",
    nysc="",
    my_degree=""
):

    query="""
    SELECT COUNT(*)
    FROM listings
    WHERE """ + FEED_FILTER + """
    """

    params=[]


    if search:

        query+=" AND(title LIKE ? OR company LIKE ? OR skills LIKE ?)"

        params.extend([
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ])


    if remote is not None:

        query+=" AND remote=?"
        params.append(remote)


    if work_style:

        query+=" AND work_style=?"
        params.append(work_style)


    if job_type:

        query+=" AND type=?"
        params.append(job_type)


    if category:

        query+=" AND category=?"
        params.append(category)


    if skill:

        query+=" AND skills LIKE ?"
        params.append(f"%{skill}%")


    if location:

        query+=" AND location LIKE ?"
        params.append(f"%{location}%")


    extra_sql, extra_params = _eligibility_filters(nysc, my_degree)
    query += extra_sql
    params.extend(extra_params)


    conn=get_conn()

    total=conn.execute(
        query,
        params
    ).fetchone()[0]

    conn.close()


    return total



def get_job(job_id):

    conn=get_conn()

    row=conn.execute(
        """
        SELECT *
        FROM listings
        WHERE id=?
        """,
        (job_id,)
    ).fetchone()

    conn.close()


    return decorate(dict(row)) if row else None



def get_sources():

    conn=get_conn()

    rows=conn.execute(
        """
        SELECT DISTINCT source
        FROM listings
        WHERE """ + FEED_FILTER + """
        """
    ).fetchall()

    conn.close()

    return [
        row["source"]
        for row in rows
    ]



def get_locations():

    conn=get_conn()

    rows=conn.execute(
        """
        SELECT location, COUNT(*) as cnt
        FROM listings
        WHERE location IS NOT NULL AND TRIM(location) != ''
          AND """ + FEED_FILTER + """
        GROUP BY location
        ORDER BY cnt DESC
        """
    ).fetchall()


    conn.close()


    return [
        row["location"]
        for row in rows
    ]


# ===========================
# Saved jobs
# ===========================

def get_saved_jobs(user_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT listings.*, saved_jobs.created_at AS saved_at
        FROM saved_jobs
        JOIN listings ON listings.id = saved_jobs.listing_id
        WHERE saved_jobs.user_id = ?
        ORDER BY saved_jobs.created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return [decorate(dict(row)) for row in rows]


def save_job(user_id, listing_id):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO saved_jobs(user_id, listing_id) VALUES (?, ?) "
            "ON CONFLICT(user_id, listing_id) DO NOTHING",
            (user_id, listing_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def unsave_job(user_id, listing_id):
    conn = get_conn()
    cur = conn.execute(
        "DELETE FROM saved_jobs WHERE user_id = ? AND listing_id = ?",
        (user_id, listing_id),
    )
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


# ===========================
# Applications
# ===========================

def get_applications(user_id):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT a.*, l.status AS listing_status, l.expires_at AS listing_expires_at,
               l.last_seen_at AS listing_last_seen_at, l.apply_url AS listing_apply_url
        FROM applications a
        LEFT JOIN listings l ON l.id = a.listing_id
        WHERE a.user_id = ? ORDER BY a.created_at DESC
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    out = []
    for row in rows:
        app = dict(row)
        if app.get("listing_id") and app.get("listing_status") is not None:
            state = decorate({
                "status": app["listing_status"],
                "expires_at": app["listing_expires_at"],
                "last_seen_at": app["listing_last_seen_at"],
            })
            app["listing_closed"] = state["is_closed"]
            app["listing_closed_reason"] = state["closed_reason"]
        else:
            app["listing_closed"] = False
            app["listing_closed_reason"] = None
        out.append(app)
    return out


def add_application(user_id, data):
    conn = get_conn()
    cur = conn.execute(
        """
        INSERT INTO applications (user_id, listing_id, title, company, location, status, applied_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            data.get("listing_id"),
            data["title"],
            data.get("company"),
            data.get("location"),
            data.get("status", "Applied"),
            data.get("applied_date"),
            data.get("notes"),
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_application(user_id, app_id, data):
    conn = get_conn()
    fields = []
    params = []
    for col in ["title", "company", "location", "status", "applied_date", "notes"]:
        if col in data:
            fields.append(f"{col} = ?")
            params.append(data[col])
    if not fields:
        conn.close()
        return False
    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.extend([app_id, user_id])
    cur = conn.execute(
        f"UPDATE applications SET {', '.join(fields)} WHERE id = ? AND user_id = ?", params
    )
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated


def delete_application(user_id, app_id):
    conn = get_conn()
    cur = conn.execute(
        "DELETE FROM applications WHERE id = ? AND user_id = ?", (app_id, user_id)
    )
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


# ===========================
# Profile (one row per user)
# ===========================

def get_profile(user_id):
    conn = get_conn()
    # Every user gets a profile row on first access — created lazily rather
    # than at signup, so this works even for a user claiming pre-existing data.
    conn.execute(
        "INSERT OR IGNORE INTO profile (user_id, about, skills) VALUES (?, '', '[]')",
        (user_id,),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM profile WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    data = dict(row)
    data["skills"] = json.loads(data["skills"]) if data["skills"] else []
    try:
        data["onboarding"] = json.loads(data["onboarding"]) if data.get("onboarding") else None
    except ValueError:
        data["onboarding"] = None
    return data


def update_profile(user_id, about=None, skills=None, onboarding=None):
    get_profile(user_id)  # ensure the row exists
    conn = get_conn()
    fields = []
    params = []
    if about is not None:
        fields.append("about = ?")
        params.append(about)
    if skills is not None:
        fields.append("skills = ?")
        params.append(json.dumps(skills))
    if onboarding is not None:
        # fresh installs that haven't re-run migrate_add_expiry.py yet
        cols = {r[1] for r in conn.execute("PRAGMA table_info(profile)").fetchall()}
        if "onboarding" not in cols:
            conn.execute("ALTER TABLE profile ADD COLUMN onboarding TEXT")
        fields.append("onboarding = ?")
        params.append(json.dumps(onboarding))
    if not fields:
        conn.close()
        return get_profile(user_id)
    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(user_id)
    conn.execute(f"UPDATE profile SET {', '.join(fields)} WHERE user_id = ?", params)
    conn.commit()
    conn.close()
    return get_profile(user_id)


def set_resume(user_id, stored_filename, original_name, resume_text=None):
    get_profile(user_id)  # ensure the row exists
    conn = get_conn()
    conn.execute(
        "UPDATE profile SET resume_filename = ?, resume_original_name = ?, "
        "resume_uploaded_at = CURRENT_TIMESTAMP, resume_text = ? WHERE user_id = ?",
        (stored_filename, original_name, resume_text, user_id),
    )
    conn.commit()
    conn.close()
    return get_profile(user_id)


def clear_resume(user_id):
    conn = get_conn()
    conn.execute(
        "UPDATE profile SET resume_filename = NULL, resume_original_name = NULL, "
        "resume_uploaded_at = NULL, resume_text = NULL WHERE user_id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()
    return get_profile(user_id)


# ===========================
# Users / auth
# ===========================

def create_user(email, password_hash=None, google_id=None, auth_provider="local"):
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, google_id, auth_provider) VALUES (?, ?, ?, ?)",
            (email.lower().strip(), password_hash, google_id, auth_provider),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_google_id(google_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE google_id = ?", (google_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def link_google_id(user_id, google_id):
    """Attaches a Google account to an existing (password-based) account
    with the same email — so someone who signed up normally can also use
    'Sign in with Google' afterward without ending up with two accounts."""
    conn = get_conn()
    conn.execute("UPDATE users SET google_id = ? WHERE id = ?", (google_id, user_id))
    conn.commit()
    conn.close()


def get_user_by_id(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def count_users():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return n


def claim_unowned_data(user_id):
    """
    One-time handoff: assigns any pre-migration rows (user_id IS NULL) to the
    given user. Called after the very first signup so existing single-user
    data isn't orphaned by the multi-user upgrade.
    """
    conn = get_conn()
    conn.execute("UPDATE saved_jobs SET user_id = ? WHERE user_id IS NULL", (user_id,))
    conn.execute("UPDATE applications SET user_id = ? WHERE user_id IS NULL", (user_id,))
    # profile is UNIQUE(user_id) — only claim the orphan row if this user
    # doesn't already have one (get_profile creates one lazily elsewhere)
    existing = conn.execute("SELECT id FROM profile WHERE user_id = ?", (user_id,)).fetchone()
    if existing is None:
        conn.execute("UPDATE profile SET user_id = ? WHERE user_id IS NULL", (user_id,))
    conn.commit()
    conn.close()


# ===========================
# Site hashes (Phase 2 scraper change detection)
# ===========================

def get_site_hash(url):
    conn = get_conn()
    row = conn.execute("SELECT content_hash FROM site_hashes WHERE url = ?", (url,)).fetchone()
    conn.close()
    return row["content_hash"] if row else None


def set_site_hash(url, content_hash):
    conn = get_conn()
    conn.execute(
        "INSERT INTO site_hashes (url, content_hash, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(url) DO UPDATE SET content_hash=excluded.content_hash, updated_at=CURRENT_TIMESTAMP",
        (url, content_hash),
    )
    conn.commit()
    conn.close()


# ===========================
# Pending submissions (Phase 3 manual submission)
# ===========================

def create_pending_submission(submission_type, value, status="pending"):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO pending_submissions (submission_type, value, status) VALUES (?, ?, ?)",
        (submission_type, value, status),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_pending_submission_status(submission_id, status):
    conn = get_conn()
    conn.execute(
        "UPDATE pending_submissions SET status = ? WHERE id = ?", (status, submission_id)
    )
    conn.commit()
    conn.close()


def get_pending_submissions(status=None):
    conn = get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM pending_submissions WHERE status = ? ORDER BY created_at DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM pending_submissions ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ===========================
# Feedback
# ===========================

def create_feedback(user_id, user_email, message, category="other"):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO feedback (user_id, user_email, category, message) VALUES (?, ?, ?, ?)",
        (user_id, user_email, category, message),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_all_feedback(status=None):
    """For you (the developer) to check — not exposed via any API route,
    just query the DB directly or call this from a one-off script."""
    conn = get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM feedback WHERE status = ? ORDER BY created_at DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM feedback ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ===========================
# Error logging
# ===========================

def log_error(source, message, detail=None, path=None, user_id=None, user_email=None,
              user_agent=None, severity="error"):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO error_logs (source, severity, message, detail, path, user_id, user_email, user_agent)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (source, severity, message, detail, path, user_id, user_email, user_agent),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_error_logs(status=None, source=None, limit=100):
    conn = get_conn()
    query = "SELECT * FROM error_logs WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if source:
        query += " AND source = ?"
        params.append(source)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def mark_error_resolved(error_id):
    conn = get_conn()
    conn.execute("UPDATE error_logs SET status = 'resolved' WHERE id = ?", (error_id,))
    conn.commit()
    conn.close()


# ===========================
# Analytics events
# ===========================

def log_event(event_name, event_data=None, user_id=None):
    """Analytics must never break the app: if the database is busy, drop the event
    (and don't trigger an error-alert email) instead of failing the request."""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO analytics_events (event_name, event_data, user_id) VALUES (?, ?, ?)",
            (event_name, event_data, user_id),
        )
        conn.commit()
    except sqlite3.OperationalError as e:
        import logging
        logging.getLogger(__name__).warning("Dropped analytics event %s: %s", event_name, e)
    finally:
        conn.close()


def get_event_summary(days=7):
    """Counts of each event_name in the last N days — the 'what do people
    actually use' view."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT event_name, COUNT(*) as count
           FROM analytics_events
           WHERE created_at >= datetime('now', ?)
           GROUP BY event_name
           ORDER BY count DESC""",
        (f"-{days} days",),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_daily_active_users(days=7):
    conn = get_conn()
    rows = conn.execute(
        """SELECT DATE(created_at) as day, COUNT(DISTINCT user_id) as active_users
           FROM analytics_events
           WHERE created_at >= datetime('now', ?) AND user_id IS NOT NULL
           GROUP BY DATE(created_at)
           ORDER BY day DESC""",
        (f"-{days} days",),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ===========================
# Listing lifecycle (expiry / closed / reports)
# ===========================

def expire_listings():
    """Sweep: flip listings whose expiry has passed to 'expired'. The feed query
    already hides them by time, so this is bookkeeping, not correctness."""
    conn = get_conn()
    cur = conn.execute(
        "UPDATE listings SET status='expired', closed_at=COALESCE(closed_at, datetime('now')) "
        "WHERE status='active' AND expires_at IS NOT NULL AND expires_at <= datetime('now')"
    )
    conn.commit()
    n = cur.rowcount
    conn.close()
    return n


def touch_listings(urls):
    """Scraper saw these URLs on the source site this run (even if it skipped
    re-parsing them). Resets the missed counter; re-opens a source-closed listing
    that is still within its expiry."""
    urls = [u for u in urls if u]
    if not urls:
        return 0
    conn = get_conn()
    n = 0
    for i in range(0, len(urls), 500):
        chunk = urls[i:i + 500]
        marks = ",".join("?" * len(chunk))
        cur = conn.execute(
            f"""UPDATE listings SET last_seen_at = datetime('now'), missed_scrapes = 0,
                  status = CASE WHEN status = 'closed' AND (expires_at IS NULL OR expires_at > datetime('now'))
                                THEN 'active' ELSE status END,
                  closed_at = CASE WHEN status = 'closed' AND (expires_at IS NULL OR expires_at > datetime('now'))
                                THEN NULL ELSE closed_at END
                WHERE apply_url IN ({marks})""",
            chunk,
        )
        n += cur.rowcount
    conn.commit()
    conn.close()
    return n


def touch_listing(url):
    return touch_listings([url])


def close_listing_by_url(url, reason="source_closed"):
    """The source page itself says the job is closed/expired — trust it immediately."""
    conn = get_conn()
    cur = conn.execute(
        "UPDATE listings SET status='closed', closed_at=datetime('now') "
        "WHERE apply_url = ? AND status = 'active'",
        (url,),
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def begin_scrape(source):
    """Call at the start of a source's scrape. Returns a handle for finish_scrape."""
    conn = get_conn()
    started_at = conn.execute("SELECT datetime('now')").fetchone()[0]
    cur = conn.execute(
        "INSERT INTO scrape_runs (source, started_at) VALUES (?, ?)", (source, started_at)
    )
    conn.commit()
    run = {"id": cur.lastrowid, "source": source, "started_at": started_at}
    conn.close()
    return run


# A run that sees fewer than this share of what we already knew is treated as a
# broken scrape (site layout changed, blocked, outage) — NOT as "everything closed".
MIN_COVERAGE_RATIO = 0.5
MIN_KNOWN_FOR_GUARD = 20


def finish_scrape(run, complete):
    """
    Call after a source's scrape. `complete` means the scraper covered the
    source's WHOLE listing index with no index-level failures (a scraper that
    caps pagination must pass False). Only then do unseen listings get a missed
    mark; MISSED_SCRAPES_TO_CLOSE consecutive misses closes them.

    Returns a summary dict (also logged in scrape_runs.note).
    """
    conn = get_conn()
    src, started = run["source"], run["started_at"]
    seen = conn.execute(
        "SELECT COUNT(*) FROM listings WHERE source=? AND last_seen_at >= ?", (src, started)
    ).fetchone()[0]
    unseen = conn.execute(
        "SELECT COUNT(*) FROM listings WHERE source=? AND status='active' AND last_seen_at < ?",
        (src, started),
    ).fetchone()[0]

    marked = closed = 0
    counted = 0
    if not complete:
        note = "partial coverage: no missed-scrape tracking"
    elif seen == 0:
        note = "saw nothing: treated as failed run"
    elif (seen + unseen) >= MIN_KNOWN_FOR_GUARD and seen < MIN_COVERAGE_RATIO * (seen + unseen):
        note = f"suspiciously low coverage ({seen} of {seen + unseen}): treated as failed run"
    else:
        counted = 1
        marked = conn.execute(
            "UPDATE listings SET missed_scrapes = COALESCE(missed_scrapes,0) + 1 "
            "WHERE source=? AND status='active' AND last_seen_at < ?",
            (src, started),
        ).rowcount
        closed = conn.execute(
            "UPDATE listings SET status='closed', closed_at=datetime('now') "
            "WHERE source=? AND status='active' AND missed_scrapes >= ?",
            (src, MISSED_SCRAPES_TO_CLOSE),
        ).rowcount
        note = f"missed marked={marked}, closed={closed}"

    conn.execute(
        "UPDATE scrape_runs SET finished_at=datetime('now'), seen_count=?, counted_as_complete=?, note=? WHERE id=?",
        (seen, counted, note, run["id"]),
    )
    conn.commit()
    conn.close()
    return {"seen": seen, "unseen": unseen, "counted": bool(counted),
            "marked_missed": marked, "closed": closed, "note": note}


def report_listing(user_id, listing_id, reason=None):
    """One report per user per listing. After REPORTS_TO_HIDE distinct reports the
    listing is hidden (under_review) until a human restores or removes it."""
    conn = get_conn()
    try:
        exists = conn.execute("SELECT id FROM listings WHERE id=?", (listing_id,)).fetchone()
        if exists is None:
            return {"found": False}
        cur = conn.execute(
            "INSERT INTO listing_reports (listing_id, user_id, reason) VALUES (?, ?, ?) "
            "ON CONFLICT(listing_id, user_id) DO NOTHING",
            (listing_id, user_id, (reason or "")[:300]),
        )
        new_report = cur.rowcount > 0
        count = conn.execute(
            "SELECT COUNT(*) FROM listing_reports WHERE listing_id=?", (listing_id,)
        ).fetchone()[0]
        conn.execute("UPDATE listings SET report_count=? WHERE id=?", (count, listing_id))
        hidden = False
        if count >= REPORTS_TO_HIDE:
            conn.execute(
                "UPDATE listings SET status='under_review', closed_at=COALESCE(closed_at, datetime('now')) "
                "WHERE id=? AND status='active'",
                (listing_id,),
            )
            hidden = True
        conn.commit()
        return {"found": True, "new_report": new_report, "report_count": count, "hidden": hidden}
    finally:
        conn.close()


def get_reported_listings(min_reports=1):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, title, company, source, apply_url, status, report_count, flag_reason FROM listings "
        "WHERE report_count >= ? OR (flag_reason IS NOT NULL AND status = 'under_review') "
        "ORDER BY report_count DESC, id DESC",
        (min_reports,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_listing_status(listing_id, status):
    """Admin: restore ('active') or remove ('closed') a reported listing."""
    if status not in ("active", "closed", "expired", "under_review"):
        raise ValueError("invalid status")
    conn = get_conn()
    if status == "active":
        conn.execute("DELETE FROM listing_reports WHERE listing_id=?", (listing_id,))
        cur = conn.execute(
            "UPDATE listings SET status='active', closed_at=NULL, report_count=0, scam_cleared=1 WHERE id=?",
            (listing_id,),
        )
    else:
        cur = conn.execute(
            "UPDATE listings SET status=?, closed_at=COALESCE(closed_at, datetime('now')) WHERE id=?",
            (status, listing_id),
        )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def purge_stale_listings(days=180):
    """Optional housekeeping for small free-tier databases: delete listings that
    have been closed/expired for `days`+ AND nobody saved, applied to or reported.
    Anything a user still references is kept."""
    conn = get_conn()
    cur = conn.execute(
        """DELETE FROM listings
           WHERE status != 'active'
             AND COALESCE(closed_at, expires_at, created_at) < datetime('now', ?)
             AND id NOT IN (SELECT listing_id FROM saved_jobs WHERE listing_id IS NOT NULL)
             AND id NOT IN (SELECT listing_id FROM applications WHERE listing_id IS NOT NULL)
             AND id NOT IN (SELECT listing_id FROM listing_reports)""",
        (f"-{days} days",),
    )
    conn.commit()
    n = cur.rowcount
    conn.close()
    return n
