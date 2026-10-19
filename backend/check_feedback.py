"""
Run this to check what beta testers have sent in. Not exposed via the API
on purpose — feedback includes people's emails, so it's kept to a local
script only you run, rather than any authenticated user being able to read
everyone else's submissions.

Usage:
  python check_feedback.py            # show all
  python check_feedback.py new        # show only unreviewed feedback
"""

import sys
from dotenv import load_dotenv

load_dotenv()

from db import get_all_feedback, get_conn


def main():
    status_filter = sys.argv[1] if len(sys.argv) > 1 else None
    items = get_all_feedback(status=status_filter)

    if not items:
        print("No feedback yet." if not status_filter else f"No feedback with status '{status_filter}'.")
        return

    for item in items:
        print("-" * 50)
        print(f"#{item['id']} | {item['category']} | {item['status']} | {item['created_at']}")
        print(f"From: {item['user_email']}")
        print(item["message"])
    print("-" * 50)
    print(f"\n{len(items)} item(s) shown.")


def mark_reviewed(feedback_id):
    """Call this manually (python -c "from check_feedback import mark_reviewed; mark_reviewed(3)")
    once you've read and acted on a piece of feedback."""
    conn = get_conn()
    conn.execute("UPDATE feedback SET status = 'reviewed' WHERE id = ?", (feedback_id,))
    conn.commit()
    conn.close()
    print(f"Marked #{feedback_id} as reviewed.")


if __name__ == "__main__":
    main()
