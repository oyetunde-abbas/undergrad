"""
One-time migration: adds saved_jobs and applications tables so Saved/Applications
data survives a page refresh instead of living only in React state.

Safe to re-run (uses CREATE TABLE IF NOT EXISTS) — won't touch the existing
588 listings rows.

Single-user for now (no auth system exists yet — that's Phase 4 stretch per
the original build plan), so there's no user_id column. If multi-user support
gets built later, both tables will need one.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "data" / "listings.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS saved_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(listing_id),
            FOREIGN KEY(listing_id) REFERENCES listings(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            status TEXT DEFAULT 'Applied',
            applied_date TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(listing_id) REFERENCES listings(id) ON DELETE SET NULL
        )
    """)

    conn.commit()
    conn.close()
    print("Migration complete — saved_jobs and applications tables ready.")


if __name__ == "__main__":
    main()
