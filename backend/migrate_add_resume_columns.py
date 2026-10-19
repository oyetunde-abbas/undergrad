"""
One-time migration: adds resume-tracking columns to the profile table so an
uploaded resume file survives a refresh, matching the same pattern used for
About-me/Skills.

Safe to re-run — checks for the columns before adding them, since SQLite's
ALTER TABLE ADD COLUMN has no IF NOT EXISTS guard.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "data" / "listings.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    existing_cols = {row[1] for row in cur.execute("PRAGMA table_info(profile)").fetchall()}

    if "resume_filename" not in existing_cols:
        cur.execute("ALTER TABLE profile ADD COLUMN resume_filename TEXT")
    if "resume_original_name" not in existing_cols:
        cur.execute("ALTER TABLE profile ADD COLUMN resume_original_name TEXT")
    if "resume_uploaded_at" not in existing_cols:
        cur.execute("ALTER TABLE profile ADD COLUMN resume_uploaded_at TIMESTAMP")

    conn.commit()
    conn.close()
    print("Migration complete — profile.resume_* columns ready.")


if __name__ == "__main__":
    main()
