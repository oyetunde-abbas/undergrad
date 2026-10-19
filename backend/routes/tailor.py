from fastapi import APIRouter, Depends, HTTPException, Request

from db import get_job, get_profile
from deps import get_current_user
from resume_tailor import tailor_resume
from rate_limit import limiter

router = APIRouter()


@router.post("/{job_id}/tailor")
@limiter.limit("10/hour")
def tailor_for_job(job_id: int, request: Request, current_user=Depends(get_current_user)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    profile = get_profile(current_user["id"])
    resume_text = profile.get("resume_text")
    if not resume_text or not resume_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Upload a resume first (PDF or DOCX) — nothing to tailor without one.",
        )

    result = tailor_resume(
        resume_text=resume_text,
        job_title=job.get("title", ""),
        job_summary=job.get("summary", ""),
        job_skills=job.get("skills", ""),
    )

    if not result:
        raise HTTPException(
            status_code=503,
            detail="Resume analysis is unavailable right now — check GEMINI_API_KEY is set, then try again.",
        )

    return result
