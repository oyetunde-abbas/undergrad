"""
Adds the listing-lifecycle schema (safe to run repeatedly):

  listings: first_seen_at, last_seen_at, expires_at, missed_scrapes, closed_at,
            dedupe_key, duplicate_of, report_count
  tables:   listing_reports (one report per user per listing), scrape_runs

Backfills existing rows. Listings with no real deadline whose default lifetime
has ALREADY run out get a short grace window (default 7 days) instead of vanishing
the moment you migrate — the next scrape then confirms or closes them.

Usage:  python migrate_add_expiry.py [--grace-days 7]
"""

import argparse
import sqlite3
from datetime import timedelta
from pathlib import Path

import eligibility
import scam_guard
from expiry import default_expiry, dedupe_key, fmt, parse_deadline, parse_ts, utcnow

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "data" / "listings.db"

NEW_COLUMNS = {
    "first_seen_at": "TIMESTAMP",
    "last_seen_at": "TIMESTAMP",
    "expires_at": "TIMESTAMP",
    "missed_scrapes": "INTEGER DEFAULT 0",
    "closed_at": "TIMESTAMP",
    "dedupe_key": "TEXT",
    "duplicate_of": "INTEGER",
    "report_count": "INTEGER DEFAULT 0",
    "flag_reason": "TEXT",
    "scam_cleared": "INTEGER DEFAULT 0",
    "nysc_req": "TEXT",
    "min_degree": "TEXT",
    "eligibility_checked": "INTEGER DEFAULT 0",
}


def migrate(conn, grace_days=7):
    cur = conn.cursor()
    existing = {r[1] for r in cur.execute("PRAGMA table_info(listings)").fetchall()}
    for col, col_type in NEW_COLUMNS.items():
        if col not in existing:
            cur.execute(f"ALTER TABLE listings ADD COLUMN {col} {col_type}")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS listing_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(listing_id, user_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scrape_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            started_at TIMESTAMP NOT NULL,
            finished_at TIMESTAMP,
            seen_count INTEGER DEFAULT 0,
            counted_as_complete INTEGER DEFAULT 0,
            note TEXT
        )
    """)
    has_profile = cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='profile'").fetchone()
    if has_profile:
        pcols = {r[1] for r in cur.execute("PRAGMA table_info(profile)").fetchall()}
        if "onboarding" not in pcols:
            cur.execute("ALTER TABLE profile ADD COLUMN onboarding TEXT")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_listings_feed ON listings(status, expires_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_listings_dedupe ON listings(dedupe_key)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_listings_source ON listings(source, status)")

    # ---- backfill rows that predate this migration
    now = utcnow()
    grace_until = fmt(now + timedelta(days=grace_days))
    rows = cur.execute(
        "SELECT id, title, company, type, deadline, created_at, status FROM listings "
        "WHERE first_seen_at IS NULL"
    ).fetchall()

    for row in rows:
        listing_id, title, company, ltype, deadline, created_at, status = row
        created = parse_ts(created_at) or now
        first_seen = fmt(created)
        parsed = parse_deadline(deadline, now=now)
        if parsed:
            expires = parsed                      # a real deadline is honoured even if past
        else:
            expires = default_expiry(created, ltype)
            if parse_ts(expires) <= now:
                expires = grace_until             # grace instead of instant disappearance
        new_status = status or "active"
        if new_status == "active" and parse_ts(expires) <= now:
            new_status = "expired"
        cur.execute(
            "UPDATE listings SET first_seen_at=?, last_seen_at=?, expires_at=?, status=?, "
            "dedupe_key=?, missed_scrapes=0 WHERE id=?",
            (first_seen, first_seen, expires, new_status, dedupe_key(title, company), listing_id),
        )

    # ---- mark cross-source duplicates (keep the oldest active one)
    cur.execute("""
        UPDATE listings SET duplicate_of = (
            SELECT MIN(l2.id) FROM listings l2
            WHERE l2.dedupe_key = listings.dedupe_key AND l2.id < listings.id AND l2.status = 'active'
        )
        WHERE dedupe_key IS NOT NULL AND status = 'active' AND duplicate_of IS NULL
    """)
    # ---- eligibility signals + scam screen for every row not yet analysed
    for rid, title, summary, status in cur.execute(
        "SELECT id, title, summary, status FROM listings WHERE COALESCE(eligibility_checked,0)=0"
    ).fetchall():
        elig = eligibility.analyse(title, summary)
        cur.execute(
            "UPDATE listings SET nysc_req=?, min_degree=?, eligibility_checked=1 WHERE id=?",
            (elig["nysc_req"], elig["min_degree"], rid),
        )
        reason = scam_guard.check(f"{title}\n{summary or ''}")
        if reason:
            cur.execute(
                "UPDATE listings SET flag_reason=?, status=CASE WHEN status='active' THEN 'under_review' ELSE status END WHERE id=?",
                (reason, rid),
            )
    conn.commit()
    return len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grace-days", type=int, default=7)
    args = parser.parse_args()
    conn = sqlite3.connect(DB_PATH)
    n = migrate(conn, grace_days=args.grace_days)
    conn.close()
    print(f"Expiry migration done. Backfilled {n} existing listings.")


if __name__ == "__main__":
    main()
