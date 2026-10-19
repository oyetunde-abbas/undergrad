"""
Backs up data/listings.db to data/backups/, timestamped, and prunes old
backups beyond a retention window. Designed to be run on a schedule (cron/
systemd timer) once deployed — a single SQLite file with no backups means
one bad disk, one bad deploy, or one accidental DELETE can lose everything.

Uses SQLite's own online backup API (not a plain file copy) so it's safe
to run even while the backend is actively serving requests — a raw
`cp listings.db backup.db` can produce a corrupted copy if a write happens
mid-copy; sqlite3's backup() method handles this correctly.

Usage:
  python backup_db.py                # run once
  Add to crontab for daily backups, e.g.:
    0 3 * * * cd /path/to/backend && venv/bin/python backup_db.py >> backup.log 2>&1
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("backup_db")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "data" / "listings.db"
BACKUP_DIR = BASE_DIR.parent / "data" / "backups"
RETENTION_DAYS = 14


def backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"listings_{timestamp}.db"

    source = sqlite3.connect(DB_PATH)
    dest = sqlite3.connect(backup_path)
    with dest:
        source.backup(dest)
    source.close()
    dest.close()

    size_mb = backup_path.stat().st_size / (1024 * 1024)
    logger.info(f"Backup created: {backup_path.name} ({size_mb:.1f} MB)")
    return backup_path


def prune_old_backups():
    cutoff = datetime.now().timestamp() - (RETENTION_DAYS * 86400)
    removed = 0
    for f in BACKUP_DIR.glob("listings_*.db"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1
    if removed:
        logger.info(f"Pruned {removed} backup(s) older than {RETENTION_DAYS} days")


def main():
    backup()
    prune_old_backups()


if __name__ == "__main__":
    main()
