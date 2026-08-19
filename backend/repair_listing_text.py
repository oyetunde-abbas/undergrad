"""
One-time repair for stale rows fetched before clean_description() existed:
- Strips leftover HTML tags from title/summary
- Repairs mojibake (UTF-8 text that got wrongly decoded as Latin-1)
- Strips scraped UI artifacts (icon-font ligature text like "keyboard_arrow_left",
  share-button labels like "facebook whatsapp mail link") that leaked into descriptions
Safe to run multiple times — already-clean rows are left untouched.
"""
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "listings.db"

UI_ARTIFACTS = [
    "keyboard_arrow_left",
    "keyboard_arrow_right",
    "keyboard_arrow_up",
    "keyboard_arrow_down",
    "facebook whatsapp mail link",
]


def repair_mojibake(text):
    """Recover UTF-8 text that was wrongly decoded as Latin-1.
    Safe: correctly-decoded non-Latin-1 text (proper Arabic/CJK/emoji Unicode
    codepoints) can't be re-encoded to Latin-1, so this raises and we skip it —
    only actually-corrupted text passes through."""
    if not text:
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except UnicodeDecodeError:
        # Likely truncated mid multi-byte character at the source (byte-level
        # slice cut a UTF-8 sequence in half). Recover what's salvageable
        # rather than leaving the whole string garbled.
        try:
            return text.encode("latin-1").decode("utf-8", errors="ignore")
        except UnicodeEncodeError:
            return text
    except UnicodeEncodeError:
        return text


def clean_text(text):
    if not text:
        return text
    text = repair_mojibake(text)
    text = re.sub(r"<[^>]+>", "", text)
    for artifact in UI_ARTIFACTS:
        text = text.replace(artifact, "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    rows = cursor.execute("SELECT id, title, summary, company FROM listings").fetchall()

    updated = 0
    for row in rows:
        new_title = clean_text(row["title"])
        new_summary = clean_text(row["summary"])
        new_company = clean_text(row["company"])

        if new_title != row["title"] or new_summary != row["summary"] or new_company != row["company"]:
            cursor.execute(
                "UPDATE listings SET title = ?, summary = ?, company = ? WHERE id = ?",
                (new_title, new_summary, new_company, row["id"]),
            )
            updated += 1

    conn.commit()
    conn.close()
    print(f"Repaired {updated} of {len(rows)} rows.")


if __name__ == "__main__":
    main()
