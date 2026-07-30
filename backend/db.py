import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "data" / "listings.db"


def get_conn():
    """Return a SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def insert_listing(listing):
    """
    Insert a listing.
    Returns True if inserted.
    Returns False if duplicate.
    """

    conn = get_conn()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO listings (
                title,
                company,
                summary,
                apply_url,
                deadline,
                location,
                remote,
                nysc_free,
                eligibility_notes,
                source,
                content_hash,
                status,
                needs_manual_review
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            listing["title"],
            listing.get("company"),
            listing.get("summary"),
            listing["apply_url"],
            listing.get("deadline"),
            listing.get("location"),
            listing.get("remote", 0),
            listing.get("nysc_free", 0),
            listing.get("eligibility_notes"),
            listing.get("source", "api"),
            listing.get("content_hash"),
            listing.get("status", "active"),
            listing.get("needs_manual_review", 0)
        ))

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        conn.close()


def get_all_listings():
   
    """Return all listings."""

    conn = get_conn()

    rows = conn.execute("""
        SELECT *
        FROM listings
        ORDER BY created_at DESC
    """).fetchall()

    conn.close()

    return [dict(row) for row in rows]
def get_jobs(
    page=1,
    limit=20,
    search="",
    remote=None,
    source="",
    location=""
):

    offset = (page - 1) * limit

    query = """
        SELECT *
        FROM listings
        WHERE 1=1
    """

    params = []

    # -------------------------
    # Search
    # -------------------------
    if search:
        query += """
        AND (
            title LIKE ?
            OR company LIKE ?
            OR summary LIKE ?
        )
        """

        params.extend([
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ])

    # -------------------------
    # Remote
    # -------------------------
    if remote is not None:
        query += " AND remote = ?"
        params.append(remote)

    # -------------------------
    # Source
    # -------------------------
    if source:
        query += " AND source = ?"
        params.append(source)

    # -------------------------
    # Location
    # -------------------------
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")

    query += """
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """

    params.extend([limit, offset])

    conn = get_conn()

    rows = conn.execute(
        query,
        params
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]
    
if __name__ == "__main__":

    listings = get_all_listings()

    print("Database connected successfully")
    print("Total listings:", len(listings))

    for job in listings[:5]:
        print(
            job["title"],
            "|",
            job["company"],
            "|",
            job["source"]
        )