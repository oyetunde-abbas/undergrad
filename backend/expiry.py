"""
Listing lifecycle helpers: deadline parsing, default expiry, duplicate keys,
and the extra fields the frontend needs (Closed / Closing soon / Checked N days ago).

All timestamps are stored as UTC strings 'YYYY-MM-DD HH:MM:SS' — the same
format SQLite's CURRENT_TIMESTAMP / datetime('now') produces — so they compare
correctly as plain strings in SQL.

Statuses:
  active        shown in the feed
  expired       deadline (or default lifetime) has passed
  closed        source stopped listing it (missed scrapes / source says closed)
  under_review  hidden after several user reports, waiting for a human
"""

import re
from datetime import datetime, timedelta, timezone

from dateutil import parser as dateparser

DEFAULT_LIFETIME_DAYS = 30
INTERNSHIP_LIFETIME_DAYS = 21
CLOSING_SOON_DAYS = 3
MISSED_SCRAPES_TO_CLOSE = 2
REPORTS_TO_HIDE = 3

# Nigeria is UTC+1 all year. A deadline of "30 Oct" means the end of 30 Oct in Nigeria.
_WAT = timezone(timedelta(hours=1))
_FMT = "%Y-%m-%d %H:%M:%S"

_ORDINAL_RE = re.compile(r"(\d)(st|nd|rd|th)\b", re.IGNORECASE)
_NO_DATE_WORDS = re.compile(
    r"asap|until filled|open until|ongoing|rolling|not specified|n/?a|immediately|as soon", re.IGNORECASE
)


def utcnow():
    return datetime.now(timezone.utc)


def fmt(dt):
    """datetime -> stored UTC string."""
    return dt.astimezone(timezone.utc).strftime(_FMT)


def parse_ts(value):
    """Stored UTC string -> aware datetime (None if empty/unparseable)."""
    if not value:
        return None
    try:
        return datetime.strptime(value[:19], _FMT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_deadline(text, now=None):
    """
    Turns a scraped deadline string into a stored UTC expiry string, or None
    if it can't be trusted. Handles ISO ('2026-11-30T00:00:00Z'), '30 October, 2026',
    'October 30, 2026', '30th Oct 2026', '30/10/2026' (day first — Nigerian style).
    Never guesses: free text like 'ASAP' or 'Open until filled' returns None.
    """
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    if not text or _NO_DATE_WORDS.search(text):
        return None
    cleaned = _ORDINAL_RE.sub(r"\1", text).replace(",", " ")
    # must contain a digit and either a month name or a numeric date separator
    if not re.search(r"\d", cleaned):
        return None
    try:
        dt = dateparser.parse(cleaned, dayfirst=True, fuzzy=False)
    except (ValueError, OverflowError, TypeError):
        return None

    now = now or utcnow()
    has_time = bool(re.search(r"\d{1,2}:\d{2}", cleaned))
    if dt.tzinfo is not None and has_time:
        expires = dt.astimezone(timezone.utc)
    else:
        # date-only (or naive time): valid through the end of that day in Nigeria
        expires = dt.replace(hour=23, minute=59, second=59, tzinfo=_WAT) if not has_time \
            else dt.replace(tzinfo=_WAT)
        expires = expires.astimezone(timezone.utc)

    # Sanity: a parse that lands years away is almost certainly wrong.
    if expires.year < 2000 or expires > now + timedelta(days=400):
        return None
    return fmt(expires)


def default_expiry(first_seen, listing_type=None):
    """No usable deadline: 30 days after first seen (21 for internships)."""
    is_internship = bool(listing_type and "intern" in str(listing_type).lower())
    days = INTERNSHIP_LIFETIME_DAYS if is_internship else DEFAULT_LIFETIME_DAYS
    return fmt(first_seen + timedelta(days=days))


_NOISE = re.compile(r"[^a-z0-9 ]+")
_FILLER = re.compile(r"\b(ltd|limited|plc|nigeria|nig|inc|llc|the|and|co)\b")


def dedupe_key(title, company):
    """
    Same role at the same company posted on two boards -> same key.
    Returns None when company is missing (too risky to merge on title alone).
    """
    if not title or not company:
        return None

    def norm(s):
        s = _NOISE.sub(" ", str(s).lower())
        s = _FILLER.sub(" ", s)
        return " ".join(s.split())

    t, c = norm(title), norm(company)
    if not t or not c:
        return None
    return f"{t}|{c}"


def decorate(job, now=None):
    """
    Adds the display fields the frontend needs, without hiding the row:
      is_closed, closed_reason, closing_soon, days_left, checked_days_ago.
    Used for Saved / Applications / job detail, which must keep showing
    closed listings (greyed, Apply disabled) instead of letting them vanish.
    """
    if job is None:
        return None
    now = now or utcnow()
    expires = parse_ts(job.get("expires_at"))
    status = job.get("status") or "active"

    past_expiry = expires is not None and expires <= now
    is_closed = status != "active" or past_expiry
    if status == "under_review":
        reason = "under_review"
    elif status == "closed":
        reason = "closed_by_source"
    elif status == "expired" or past_expiry:
        reason = "deadline_passed"
    else:
        reason = None

    days_left = None
    closing_soon = False
    if expires is not None and not is_closed:
        days_left = max(0, (expires - now).days)
        closing_soon = (expires - now) <= timedelta(days=CLOSING_SOON_DAYS)

    seen = parse_ts(job.get("last_seen_at")) or parse_ts(job.get("created_at"))
    checked = max(0, (now - seen).days) if seen else None

    job["is_closed"] = is_closed
    job["closed_reason"] = reason
    job["closing_soon"] = closing_soon
    job["days_left"] = days_left
    job["checked_days_ago"] = checked
    return job
