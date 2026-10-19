"""
One-time migration: adds resume_text to the profile table — the actual
extracted text content of the uploaded resume, not just the skills list
pulled from it. Needed for the "tailor my resume for this job" feature,
which needs the full resume content to work with, not just a skill list.

Safe to re-run.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "data" / "listings.db"


def column_exists(cur, table, column):
    cols = {row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()}
    return column in cols


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if not column_exists(cur, "profile", "resume_text"):
        cur.execute("ALTER TABLE profile ADD COLUMN resume_text TEXT")
        print("Added resume_text column.")
    else:
        print("Already migrated — nothing to do.")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
