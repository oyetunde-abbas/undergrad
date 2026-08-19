import os
import re
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is not set. Copy .env.example to .env and fill in a "
        "generated secret before starting the server."
    )

JWT_ALGORITHM = "HS256"
TOKEN_EXPIRY_DAYS = 30

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email):
    return bool(EMAIL_RE.match(email or ""))


def is_valid_password(password):
    # Kept simple on purpose — length is the requirement that actually matters
    # for a small personal-use app; no forced special-character rules.
    return bool(password) and len(password) >= 8


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, password_hash):
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id, email):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + timedelta(days=TOKEN_EXPIRY_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token):
    """Returns the payload dict, or None if the token is invalid/expired."""
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
