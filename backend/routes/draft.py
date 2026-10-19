from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

import drafter
from db import get_job, get_profile
from deps import get_current_user
from rate_limit import limiter

router = APIRouter()


class DraftBody(BaseModel):
    name: Optional[str] = None


@router.post("/{job_id}/draft")
@limiter.limit("15/hour")
def draft_application(request: Request, job_id: int, body: DraftBody, current_user=Depends(get_current_user)):
    """Prepares (never sends) an application email or portal pitch for the student to review."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("is_closed"):
        raise HTTPException(status_code=400, detail="This listing is closed — nothing to apply to.")
    profile = get_profile(current_user["id"]) or {}
    return drafter.build_draft(
        job,
        name=body.name or current_user.get("name"),
        profile=profile,
        onboarding=profile.get("onboarding") or {},
        resume_text=profile.get("resume_text"),
    )
