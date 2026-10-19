"""
Run this AFTER fetch_apis.py on whichever machine does the actual scraping
(your laptop, most likely). Pushes every listing currently in your local
data/listings.db to the deployed backend's /admin/sync-listings endpoint.

This is what lets a free host with restricted outbound internet access
(like PythonAnywhere's free tier) still serve a job aggregator — the
scraping happens here, where you have full internet access, and only the
already-scraped results get sent to the deployed backend as a normal
inbound request.

Setup:
  1. On the DEPLOYED backend's .env, set SYNC_API_KEY to a random secret
     (generate with: python -c "import secrets; print(secrets.token_hex(32))")
  2. On THIS machine's .env (or just export as an environment variable),
     set the same SYNC_API_KEY, plus SYNC_TARGET_URL pointing at your
     deployed backend, e.g.:
       SYNC_TARGET_URL=https://yourusername.pythonanywhere.com

Usage (run after fetch_apis.py, e.g. as the next line in the same daily
Task Scheduler job):
  python sync_to_remote.py
"""

import os
import sys
import logging
import sqlite3
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sync_to_remote")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "data" / "listings.db"

SYNC_API_KEY = os.getenv("SYNC_API_KEY")
SYNC_TARGET_URL = os.getenv("SYNC_TARGET_URL")
BATCH_SIZE = 100

# Only these fields get sent — matches routes/admin.py's ListingIn schema.
# Deliberately excludes the local auto-increment `id`, since the remote
# database has its own ids; rows are matched/deduped on apply_url instead
# (same UPSERT logic insert_listing() always uses).
SYNC_FIELDS = [
    "title", "company", "summary", "apply_url", "deadline", "location",
    "remote", "nysc_free", "eligibility_notes", "source", "content_hash",
    "status", "needs_manual_review", "work_style", "type", "category",
    "skills", "experience_level",
    # lifecycle: the scraping machine is the source of truth for these
    "first_seen_at", "last_seen_at", "expires_at",
]


def fetch_local_listings():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"SELECT {', '.join(SYNC_FIELDS)} FROM listings").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def push_batch(batch):
    resp = requests.post(
        f"{SYNC_TARGET_URL}/admin/sync-listings",
        json={"listings": batch},
        headers={"X-Sync-Key": SYNC_API_KEY},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    if not SYNC_API_KEY or not SYNC_TARGET_URL:
        logger.error(
            "SYNC_API_KEY and/or SYNC_TARGET_URL not set — see the top of this "
            "file for setup instructions. Nothing was synced."
        )
        sys.exit(1)

    listings = fetch_local_listings()
    logger.info(f"Found {len(listings)} local listings to sync")

    total_processed, total_failed = 0, 0
    for i in range(0, len(listings), BATCH_SIZE):
        batch = listings[i:i + BATCH_SIZE]
        try:
            result = push_batch(batch)
            total_processed += result.get("processed", 0)
            total_failed += result.get("failed", 0)
            logger.info(f"Batch {i // BATCH_SIZE + 1}: {result}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Batch {i // BATCH_SIZE + 1} failed to send: {e}")

    logger.info(f"Sync complete: {total_processed} processed, {total_failed} failed")


if __name__ == "__main__":
    main()
