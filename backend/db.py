import sqlite3
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "data" / "listings.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def insert_listing(listing):

    conn = get_conn()
    cursor = conn.cursor()

    try:

        cursor.execute("""
        INSERT INTO listings(
            title,
            company,
            summary,
            apply_url,
            deadline,
            location,
            remote,
            work_style,
            type,
            category,
            skills,
            experience_level,
            source,
            content_hash,
            status,
            needs_manual_review
        )

        VALUES(
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
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
            experience_level=excluded.experience_level

        """,

        (
            listing["title"],
            listing.get("company"),
            listing.get("summary"),
            listing["apply_url"],
            listing.get("deadline"),
            listing.get("location"),

            listing.get("remote",0),
            listing.get("work_style",""),

            listing.get("type","Internship"),
            listing.get("category","Technology"),

            listing.get("skills",""),
            listing.get("experience_level","Entry Level"),

            listing.get("source","api"),
            listing.get("content_hash"),

            listing.get("status","active"),
            listing.get("needs_manual_review",0)
        ))


        conn.commit()
        return True


    except sqlite3.IntegrityError:
        return False


    finally:
        conn.close()



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
    sort="newest"
):

    offset=(page-1)*limit


    query="""
    SELECT *
    FROM listings
    WHERE 1=1
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
        dict(row)
        for row in rows
    ]




def count_jobs(
    search="",
    remote=None,
    work_style="",
    job_type="",
    category="",
    skill="",
    location=""
):

    query="""
    SELECT COUNT(*)
    FROM listings
    WHERE 1=1
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


    return dict(row) if row else None



def get_sources():

    conn=get_conn()

    rows=conn.execute(
        """
        SELECT DISTINCT source
        FROM listings
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
    return [dict(row) for row in rows]


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
        "SELECT * FROM applications WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


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
    return data


def update_profile(user_id, about=None, skills=None):
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
    if not fields:
        conn.close()
        return get_profile(user_id)
    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(user_id)
    conn.execute(f"UPDATE profile SET {', '.join(fields)} WHERE user_id = ?", params)
    conn.commit()
    conn.close()
    return get_profile(user_id)


def set_resume(user_id, stored_filename, original_name):
    get_profile(user_id)  # ensure the row exists
    conn = get_conn()
    conn.execute(
        "UPDATE profile SET resume_filename = ?, resume_original_name = ?, "
        "resume_uploaded_at = CURRENT_TIMESTAMP WHERE user_id = ?",
        (stored_filename, original_name, user_id),
    )
    conn.commit()
    conn.close()
    return get_profile(user_id)


def clear_resume(user_id):
    conn = get_conn()
    conn.execute(
        "UPDATE profile SET resume_filename = NULL, resume_original_name = NULL, "
        "resume_uploaded_at = NULL WHERE user_id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()
    return get_profile(user_id)


# ===========================
# Users / auth
# ===========================

def create_user(email, password_hash):
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email.lower().strip(), password_hash),
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