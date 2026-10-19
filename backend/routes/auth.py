import os
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    is_valid_email,
    is_valid_password,
)
from db import (
    create_user,
    get_user_by_email,
    get_user_by_google_id,
    link_google_id,
    count_users,
    claim_unowned_data,
)
from deps import get_current_user, COOKIE_NAME
from rate_limit import limiter

logger = logging.getLogger("auth")
router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# Cookies marked "Secure" are only ever sent over HTTPS — correct and required
# for real deployment, but it would silently block login when testing locally
# over plain http://localhost. COOKIE_SECURE should be set to "true" in the
# production .env once deployed behind real HTTPS; defaults to off so local
# development keeps working out of the box.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days, matches the JWT's own expiry


class SignupRequest(BaseModel):
    email: str
    password: str
    website: str = ""  # honeypot — real users never see or fill this field;
                        # a non-empty value means it's very likely a bot


class LoginRequest(BaseModel):
    email: str
    password: str


class GoogleAuthRequest(BaseModel):
    id_token: str  # the credential JWT Google's Sign-In button hands to the frontend


def _user_out(user):
    return {"id": user["id"], "email": user["email"]}


def _set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,      # JavaScript can never read this — the actual XSS protection
        secure=COOKIE_SECURE,
        samesite="lax",     # blocks cross-site POST/PUT/DELETE (the real CSRF vectors)
        path="/",
    )


@router.post("/signup")
@limiter.limit("5/hour")
def signup(request: Request, response: Response, body: SignupRequest):
    if body.website.strip():
        # honeypot tripped — behave exactly like a normal validation
        # rejection so a bot can't distinguish this from any other failure
        # and adapt around it
        raise HTTPException(status_code=400, detail="Enter a valid email address")

    email = body.email.strip()
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    if not is_valid_password(body.password):
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if get_user_by_email(email):
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    is_first_user = count_users() == 0

    user_id = create_user(email, hash_password(body.password))

    if is_first_user:
        # Existing pre-auth data (saved jobs, applications, profile) gets
        # handed to whoever signs up first, so the upgrade to multi-user
        # doesn't orphan anything.
        claim_unowned_data(user_id)

    token = create_access_token(user_id, email.lower())
    _set_auth_cookie(response, token)
    return {"token": token, "user": {"id": user_id, "email": email.lower()}}


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, response: Response, body: LoginRequest):
    user = get_user_by_email(body.email.strip())
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token(user["id"], user["email"])
    _set_auth_cookie(response, token)
    return {"token": token, "user": _user_out(user)}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"logged_out": True}


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    return _user_out(current_user)


@router.post("/google")
@limiter.limit("10/minute")
def google_auth(request: Request, response: Response, body: GoogleAuthRequest):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Google Sign-In isn't configured on this server yet.",
        )

    try:
        payload = google_id_token.verify_oauth2_token(
            body.id_token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        # Covers: bad signature, expired token, wrong audience (someone else's
        # client ID), malformed token — anything that means this isn't a
        # genuine, freshly-issued token for THIS app.
        logger.warning(f"Google token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Could not verify Google sign-in")
    except Exception as e:
        # Covers transport-level failures (e.g. couldn't reach Google's
        # servers to fetch their signing certs) — a temporary problem, not
        # a sign the token itself is invalid, so it gets a different,
        # honest error message rather than "could not verify sign-in".
        logger.error(f"Google Sign-In temporarily unavailable: {e}")
        raise HTTPException(
            status_code=503,
            detail="Google Sign-In is temporarily unavailable — try again in a moment, or use email/password.",
        )

    google_sub = payload["sub"]  # Google's permanent, unique ID for this account
    email = payload.get("email")
    email_verified = payload.get("email_verified", False)

    if not email or not email_verified:
        raise HTTPException(
            status_code=401,
            detail="Your Google account's email isn't verified — please verify it with Google first.",
        )
    email = email.lower().strip()

    # 1. Already linked — straightforward login
    user = get_user_by_google_id(google_sub)

    # 2. Not linked yet, but an account with this email already exists
    #    (e.g. they originally signed up with a password) — link it rather
    #    than creating a confusing second account for the same person.
    if not user:
        existing = get_user_by_email(email)
        if existing:
            link_google_id(existing["id"], google_sub)
            user = existing

    # 3. Genuinely new — create a fresh Google-only account
    is_first_user = False
    if not user:
        is_first_user = count_users() == 0
        new_id = create_user(email, password_hash=None, google_id=google_sub, auth_provider="google")
        user = {"id": new_id, "email": email}

    if is_first_user:
        claim_unowned_data(user["id"])

    token = create_access_token(user["id"], email)
    _set_auth_cookie(response, token)
    return {"token": token, "user": {"id": user["id"], "email": email}}
