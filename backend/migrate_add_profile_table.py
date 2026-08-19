"""
One-time migration: adds a `profile` table so the About-me text and Skills
list on the Profile page survive a refresh instead of living only in React
state.

Single-user, single-row table (id is always 1) — matches the no-auth
single-user approach used for saved_jobs/applications. Safe to re-run
(CREATE TABLE IF NOT EXISTS + INSERT OR IGNORE), won't touch existing data.
"""

import sqlite3
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "data" / "listings.db"

DEFAULT_ABOUT = (
    "Final-year Computer Science student at KWASU with hands-on AWS experience "
    "from a SIWES placement at UBA (IAM, VPC, EC2), and currently in the Udacity "
    "x AWS AI & ML Scholars Program. Built a DenseNet121 model for diabetic "
    "retinopathy detection at 96.19% accuracy. Looking for remote or entry-level "
    "roles in cloud, DevOps, or ML engineering."
)

DEFAULT_SKILLS = [
    "Python", "AWS (IAM, VPC, EC2)", "SQL", "React", "FastAPI",
    "Machine Learning", "Git", "REST APIs",
]


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            about TEXT NOT NULL DEFAULT '',
            skills TEXT NOT NULL DEFAULT '[]',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute(
        "INSERT OR IGNORE INTO profile (id, about, skills) VALUES (1, ?, ?)",
        (DEFAULT_ABOUT, json.dumps(DEFAULT_SKILLS)),
    )

    conn.commit()
    conn.close()
    print("Migration complete — profile table ready.")


if __name__ == "__main__":
    main()
