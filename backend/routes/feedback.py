from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel

from db import create_feedback
from deps import get_current_user
from notify import send_feedback_email
from rate_limit import limiter

router = APIRouter()

VALID_CATEGORIES = {"bug", "suggestion", "other"}


class FeedbackRequest(BaseModel):
    message: str
    category: Optional[str] = "other"


@router.post("")
@limiter.limit("20/hour")
def submit_feedback(request: Request, body: FeedbackRequest, background_tasks: BackgroundTasks, current_user=Depends(get_current_user)):
    category = body.category if body.category in VALID_CATEGORIES else "other"
    feedback_id = create_feedback(
        user_id=current_user["id"],
        user_email=current_user["email"],
        message=body.message.strip(),
        category=category,
    )

    # Runs AFTER the response is sent, so a slow or broken SMTP connection
    # never makes the person submitting feedback sit and wait for it.
    background_tasks.add_task(send_feedback_email, feedback_id, category, body.message.strip(), current_user["email"])

    return {"submitted": True, "id": feedback_id}
