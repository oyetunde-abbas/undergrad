import sqlite3
from pathlib import Path

# Project paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
DB_PATH = DATA_DIR / "listings.db"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ===========================
# Main listings table
# ===========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company TEXT,
    summary TEXT,
    apply_url TEXT UNIQUE,
    deadline TEXT,
    location TEXT,
    remote INTEGER DEFAULT 0,
    nysc_free INTEGER DEFAULT 0,
    eligibility_notes TEXT,
    source TEXT,
    content_hash TEXT,
    status TEXT DEFAULT 'active',
    needs_manual_review INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# ===========================
# Pending manual submissions
# ===========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS pending_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_type TEXT,
    value TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# ===========================
# Site hashes
# ===========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS site_hashes (
    url TEXT PRIMARY KEY,
    content_hash TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print(f"Database created successfully!")
print(f"Location: {DB_PATH}")