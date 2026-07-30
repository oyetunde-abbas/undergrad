import sqlite3
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
        SELECT DISTINCT location
        FROM listings
        WHERE location IS NOT NULL
        """
    ).fetchall()


    conn.close()


    return [
        row["location"]
        for row in rows
    ]