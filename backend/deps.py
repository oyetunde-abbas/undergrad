from fastapi import Header, HTTPException

from auth_utils import decode_access_token
from db import get_user_by_id


def get_current_user(authorization: str = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization[len("Bearer "):]
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session — please log in again")

    user = get_user_by_id(int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists")

    return user
