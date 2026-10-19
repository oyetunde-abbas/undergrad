"""
One-time migration: adds a `feedback` table so beta testers can send bug
reports/suggestions from the Profile page, tied to their account (so you
know who sent what) plus their email captured directly for easy follow-up.

Safe to re-run (CREATE TABLE IF NOT EXISTS).
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "data" / "listings.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_email TEXT,
            category TEXT DEFAULT 'other',
            message TEXT NOT NULL,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)

    conn.commit()
    conn.close()
    print("Migration complete — feedback table ready.")


if __name__ == "__main__":
    main()
