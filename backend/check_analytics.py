"""
Run this to see what features people actually use, and how many active
users you have.

Usage:
  python check_analytics.py           # last 7 days
  python check_analytics.py 30        # last 30 days
"""

import sys
from dotenv import load_dotenv

load_dotenv()

from db import get_event_summary, get_daily_active_users


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7

    print(f"=== Event counts, last {days} days ===")
    events = get_event_summary(days=days)
    if not events:
        print("No events logged yet.")
    for e in events:
        print(f"  {e['event_name']:30} {e['count']}")

    print(f"\n=== Daily active users, last {days} days ===")
    dau = get_daily_active_users(days=days)
    if not dau:
        print("No user activity logged yet.")
    for d in dau:
        print(f"  {d['day']}   {d['active_users']} active user(s)")


if __name__ == "__main__":
    main()
