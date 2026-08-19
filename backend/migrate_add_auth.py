"""
One-time migration: adds a `users` table and reworks saved_jobs, applications,
and profile so each row belongs to a user_id instead of being single-user.

Existing data (saved jobs, applications, the one profile row) is preserved
with user_id = NULL. The first account ever created via POST /auth/signup
automatically "claims" all NULL-owned rows — see routes/auth.py. This means
existing data survives the upgrade without needing a manual data-assignment
step.

saved_jobs and profile both need to be rebuilt (not just ALTER TABLE ADD
COLUMN) because their existing constraints (UNIQUE(listing_id), CHECK(id=1))
don't make sense once multiple users can each save the same listing or have
their own profile row. applications only needs a plain ADD COLUMN.

Safe to re-run — every step checks before acting.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "data" / "listings.db"


def table_exists(cur, name):
    return cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def column_exists(cur, table, column):
    cols = {row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()}
    return column in cols


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # --- users table ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --- saved_jobs: needs UNIQUE(listing_id) -> UNIQUE(user_id, listing_id) ---
    if not column_exists(cur, "saved_jobs", "user_id"):
        cur.execute("ALTER TABLE saved_jobs RENAME TO saved_jobs_old")
        cur.execute("""
            CREATE TABLE saved_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                listing_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, listing_id),
                FOREIGN KEY(listing_id) REFERENCES listings(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            INSERT INTO saved_jobs (id, user_id, listing_id, created_at)
            SELECT id, NULL, listing_id, created_at FROM saved_jobs_old
        """)
        cur.execute("DROP TABLE saved_jobs_old")

    # --- applications: simple ADD COLUMN, no constraint conflict ---
    if not column_exists(cur, "applications", "user_id"):
        cur.execute("ALTER TABLE applications ADD COLUMN user_id INTEGER REFERENCES users(id)")

    # --- profile: was a CHECK(id=1) singleton, needs to become one-row-per-user ---
    if not column_exists(cur, "profile", "user_id"):
        cur.execute("ALTER TABLE profile RENAME TO profile_old")
        cur.execute("""
            CREATE TABLE profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                about TEXT NOT NULL DEFAULT '',
                skills TEXT NOT NULL DEFAULT '[]',
                resume_filename TEXT,
                resume_original_name TEXT,
                resume_uploaded_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            INSERT INTO profile (id, user_id, about, skills, resume_filename,
                                  resume_original_name, resume_uploaded_at, updated_at)
            SELECT id, NULL, about, skills, resume_filename,
                   resume_original_name, resume_uploaded_at, updated_at
            FROM profile_old
        """)
        cur.execute("DROP TABLE profile_old")

    conn.commit()
    conn.close()
    print("Migration complete — users table ready; saved_jobs/applications/profile now scoped by user_id (existing rows kept as unclaimed / user_id=NULL).")


if __name__ == "__main__":
    main()
