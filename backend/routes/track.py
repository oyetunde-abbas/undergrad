import json
import logging
from typing import Optional

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel

from db import log_error, log_event
from auth_utils import decode_access_token
from db import get_user_by_id

logger = logging.getLogger("track")
router = APIRouter()


def _optional_user(authorization: Optional[str]):
    """Same idea as deps.get_current_user, but never raises — tracking
    should work whether or not someone's logged in (e.g. an error on the
    login screen itself, before there's any token yet)."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    payload = decode_access_token(authorization[len("Bearer "):])
    if not payload:
        return None
    return get_user_by_id(int(payload["sub"]))


class FrontendErrorRequest(BaseModel):
    message: str
    stack: Optional[str] = None
    path: Optional[str] = None
    severity: Optional[str] = "error"


class EventRequest(BaseModel):
    event_name: str
    event_data: Optional[dict] = None


@router.post("/error")
def report_frontend_error(
    body: FrontendErrorRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    user = _optional_user(authorization)
    log_error(
        source="frontend",
        severity=body.severity if body.severity in ("error", "warning") else "error",
        message=body.message[:500],
        detail=body.stack[:3000] if body.stack else None,
        path=body.path,
        user_id=user["id"] if user else None,
        user_email=user["email"] if user else None,
        user_agent=request.headers.get("user-agent"),
    )
    return {"logged": True}


@router.post("/event")
def track_event(
    body: EventRequest,
    authorization: Optional[str] = Header(default=None),
):
    user = _optional_user(authorization)
    event_data_str = json.dumps(body.event_data) if body.event_data else None
    log_event(
        event_name=body.event_name[:100],
        event_data=event_data_str,
        user_id=user["id"] if user else None,
    )
    return {"logged": True}
