"""
One-time migration: adds two tables for monitoring —

  error_logs — every unhandled backend exception AND every reported
  frontend error, in one place, with enough context (path/user/traceback
  or stack) to actually debug from.

  analytics_events — lightweight usage tracking: page views, feature use,
  PWA install events. Deliberately minimal — event name + timestamp +
  optional user_id, nothing invasive (no fingerprinting, no third-party
  tracker, stays entirely in your own database).

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
        CREATE TABLE IF NOT EXISTS error_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,           -- 'backend' or 'frontend'
            severity TEXT DEFAULT 'error',  -- 'error' or 'warning'
            message TEXT NOT NULL,
            detail TEXT,                    -- traceback (backend) or stack trace (frontend)
            path TEXT,                      -- request path / page view where it happened
            user_id INTEGER,
            user_email TEXT,
            user_agent TEXT,
            status TEXT DEFAULT 'new',      -- 'new' or 'resolved'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS analytics_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,       -- e.g. 'page_view', 'pwa_installed', 'job_saved'
            event_data TEXT,                -- small JSON blob, e.g. {"page": "explore"}
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("Migration complete — error_logs and analytics_events tables ready.")


if __name__ == "__main__":
    main()
