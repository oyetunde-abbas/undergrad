import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "data" / "listings.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

new_columns = {
    "work_style": "TEXT",
    "type": "TEXT DEFAULT 'Internship'",
    "category": "TEXT DEFAULT 'Technology'",
    "skills": "TEXT",
    "experience_level": "TEXT DEFAULT 'Entry Level'",
}

cursor.execute("PRAGMA table_info(listings)")
existing = {row[1] for row in cursor.fetchall()}

for col, col_type in new_columns.items():
    if col not in existing:
        cursor.execute(f"ALTER TABLE listings ADD COLUMN {col} {col_type}")
        print(f"Added column: {col}")
    else:
        print(f"Already exists: {col}")

conn.commit()
conn.close()
print("Migration done.")
