"""
Run this to see what's actually breaking, on either end.

Usage:
  python check_errors.py                # last 100, all sources
  python check_errors.py new            # only unresolved
  python check_errors.py backend        # only backend errors
  python check_errors.py frontend       # only frontend errors
"""

import sys
from dotenv import load_dotenv

load_dotenv()

from db import get_error_logs, mark_error_resolved


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    status = arg if arg == "new" else None
    source = arg if arg in ("backend", "frontend") else None

    items = get_error_logs(status=status, source=source)

    if not items:
        print("No errors logged. 🎉")
        return

    for item in items:
        print("-" * 60)
        print(f"#{item['id']} | {item['source']} | {item['severity']} | {item['status']} | {item['created_at']}")
        if item.get("path"):
            print(f"Path: {item['path']}")
        if item.get("user_email"):
            print(f"User: {item['user_email']}")
        print(f"Message: {item['message']}")
        if item.get("detail"):
            print(f"Detail:\n{item['detail'][:800]}")
    print("-" * 60)
    print(f"\n{len(items)} item(s) shown.")


def resolve(error_id):
    mark_error_resolved(error_id)
    print(f"Marked #{error_id} as resolved.")


if __name__ == "__main__":
    main()
