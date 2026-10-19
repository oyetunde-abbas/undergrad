from typing import Optional

from fastapi import Header, HTTPException, Request

from auth_utils import decode_access_token
from db import get_user_by_id

COOKIE_NAME = "undergrad_token"


def _extract_token(request: Request, authorization: Optional[str]):
    # Cookie first — this is what the web frontend actually relies on.
    # httpOnly means JavaScript can never read this value, even via XSS.
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token:
        return cookie_token

    # Authorization header fallback — kept for API testing (curl/Postman)
    # and any future non-browser client (a native app, for example) that
    # can't rely on cookie jars the way a browser does. This doesn't weaken
    # the web app's XSS protection, since the web frontend itself never
    # stores or sends a token this way anymore.
    if authorization and authorization.startswith("Bearer "):
        return authorization[len("Bearer "):]

    return None


def get_current_user(request: Request, authorization: Optional[str] = Header(default=None)):
    token = _extract_token(request, authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session — please log in again")

    user = get_user_by_id(int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")

    return user
