"""
One-time backfill: replace the fake default work_style/type/category/skills/
experience_level values on existing rows with real values from tag_listings.infer_tags().

Safe to re-run — it just recomputes and overwrites these five columns for every
row based on that row's own title/summary/remote, nothing else changes.
"""

import sqlite3
from tag_listings import infer_tags

DB_PATH = "../data/listings.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id, title, summary, remote FROM listings")
    rows = cur.fetchall()
    print(f"Backfilling tags for {len(rows)} rows...")

    updated = 0
    for row_id, title, summary, remote in rows:
        tags = infer_tags(title, summary, remote)
        cur.execute(
            """
            UPDATE listings
            SET work_style = ?, type = ?, category = ?, skills = ?, experience_level = ?
            WHERE id = ?
            """,
            (tags["work_style"], tags["type"], tags["category"], tags["skills"], tags["experience_level"], row_id),
        )
        updated += 1

    conn.commit()
    conn.close()
    print(f"Done — updated {updated} rows.")


if __name__ == "__main__":
    main()
