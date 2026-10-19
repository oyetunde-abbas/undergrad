"""
Sends an email notification whenever a beta tester submits feedback, using
Gmail's SMTP server with an "app password" (not your real Gmail password —
see setup notes below).

IMPORTANT — this has NOT been tested against real Gmail SMTP. This sandbox
can't reach smtp.gmail.com (network-restricted), so what's verified is: the
email content builds correctly, and every failure mode (missing
credentials, SMTP errors) degrades gracefully instead of crashing the
feedback submission — a failed email should NEVER cause someone's feedback
to be lost or the request to error out, since it's already safely in the
database by the time this runs.

Setup (on whichever machine actually runs the backend):
  1. Use a Gmail account (a dedicated one, not your main personal one, is
     often cleaner — but your existing one works fine too).
  2. Turn on 2-Step Verification on that account (required for app passwords).
  3. Go to https://myaccount.google.com/apppasswords and generate an app
     password for "Mail". You'll get a 16-character code — that's what goes
     in .env, NOT your real Gmail password.
  4. Add to .env:
       GMAIL_ADDRESS=youraccount@gmail.com
       GMAIL_APP_PASSWORD=the16charactercode
       FEEDBACK_NOTIFY_EMAIL=oyetundeabbas@gmail.com
     (FEEDBACK_NOTIFY_EMAIL is where notifications get SENT — can be the
     same address as GMAIL_ADDRESS, or a different inbox you actually check)

If these env vars aren't set, notifications are silently skipped (logged,
not crashed) — feedback still gets saved either way, you'd just need to run
check_feedback.py manually until email's configured.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText

logger = logging.getLogger("notify")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _smtp_configured():
    return bool(os.getenv("GMAIL_ADDRESS") and os.getenv("GMAIL_APP_PASSWORD") and os.getenv("FEEDBACK_NOTIFY_EMAIL"))


def send_feedback_email(feedback_id, category, message, user_email):
    """
    Fire-and-forget: sends a notification email, or logs and gives up
    quietly if anything goes wrong. Never raises — a broken email setup
    should never affect the feedback submission itself.
    """
    if not _smtp_configured():
        logger.info(
            "Email notifications not configured (missing GMAIL_ADDRESS / "
            "GMAIL_APP_PASSWORD / FEEDBACK_NOTIFY_EMAIL in .env) — skipping. "
            "Feedback is still saved; check it with check_feedback.py."
        )
        return False

    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")
    notify_to = os.getenv("FEEDBACK_NOTIFY_EMAIL")

    subject = f"[Undergrad] New {category} feedback (#{feedback_id})"
    body = (
        f"New feedback submitted.\n\n"
        f"From: {user_email}\n"
        f"Category: {category}\n\n"
        f"{message}\n\n"
        f"---\n"
        f"Reply from your own inbox to reach them, or check "
        f"`python check_feedback.py` for the full log."
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = notify_to

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(gmail_address, gmail_password)
            server.sendmail(gmail_address, [notify_to], msg.as_string())
        logger.info(f"Feedback notification email sent for #{feedback_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send feedback notification email: {e}")
        return False


def send_error_alert_email(path, error_message, traceback_text):
    """
    Same fire-and-forget pattern as send_feedback_email, but for backend
    crashes. Deliberately truncates the traceback in the email body — full
    detail is always in error_logs / check_errors.py, the email is just the
    'hey, something broke' ping.
    """
    if not _smtp_configured():
        logger.info("Email notifications not configured — skipping error alert email.")
        return False

    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")
    notify_to = os.getenv("FEEDBACK_NOTIFY_EMAIL")

    subject = f"[Undergrad] Backend error on {path}"
    body = (
        f"An unhandled error occurred.\n\n"
        f"Path: {path}\n"
        f"Error: {error_message}\n\n"
        f"Traceback (truncated):\n{traceback_text[:1500]}\n\n"
        f"---\n"
        f"Full detail: `python check_errors.py`"
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = notify_to

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(gmail_address, gmail_password)
            server.sendmail(gmail_address, [notify_to], msg.as_string())
        logger.info(f"Error alert email sent for {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to send error alert email: {e}")
        return False
