"""
One-time migration: adds Google Sign-In support to the users table.

password_hash was originally NOT NULL (every account had a password).
Google-authenticated accounts don't have one, so this needs to become
nullable — which SQLite can't do with a plain ALTER COLUMN, hence the
rebuild-and-copy pattern already used for saved_jobs/profile in earlier
migrations.

Adds:
  - google_id (nullable, unique) — Google's stable per-user identifier
  - auth_provider ('local' or 'google') — which way the account was created

Existing password-based accounts are preserved exactly as-is, with
auth_provider set to 'local'.

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

    if column_exists(cur, "users", "google_id"):
        print("Already migrated — nothing to do.")
        conn.close()
        return

    cur.execute("ALTER TABLE users RENAME TO users_old")
    cur.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            google_id TEXT UNIQUE,
            auth_provider TEXT NOT NULL DEFAULT 'local',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        INSERT INTO users (id, email, password_hash, google_id, auth_provider, created_at)
        SELECT id, email, password_hash, NULL, 'local', created_at FROM users_old
    """)
    cur.execute("DROP TABLE users_old")

    conn.commit()
    conn.close()
    print("Migration complete — users table now supports Google Sign-In.")


if __name__ == "__main__":
    main()
