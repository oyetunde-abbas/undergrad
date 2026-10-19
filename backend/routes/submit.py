import logging
from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from deps import get_current_user
from db import insert_listing, create_pending_submission, update_pending_submission_status
from extract import extract_job_posting
from llm_fallback import extract_with_llm
from tag_listings import infer_tags
from rate_limit import limiter

logger = logging.getLogger("submit")
router = APIRouter()

FETCH_TIMEOUT = 15
HEADERS = {"User-Agent": "UndergradJobAggregator/1.0 (personal project; user-submitted link)"}


class SubmissionRequest(BaseModel):
    # exactly one of these should be provided
    url: Optional[str] = None
    text: Optional[str] = None


def _build_listing(extracted, source_label, apply_url=None):
    title = extracted.get("title")
    summary = extracted.get("summary") or ""
    remote = 1 if extracted.get("remote") else 0
    if not remote and "remote" in (extracted.get("location") or "").lower():
        remote = 1

    tags = infer_tags(title, summary, remote)

    return {
        "title": title,
        "company": extracted.get("company"),
        "summary": summary[:2000],
        "apply_url": apply_url,
        "deadline": extracted.get("deadline"),
        "location": extracted.get("location") or "Nigeria",
        "remote": remote,
        "work_style": tags.get("work_style"),
        "type": extracted.get("employment_type") or tags.get("type"),
        "category": tags.get("category"),
        "skills": tags.get("skills"),
        "experience_level": tags.get("experience_level"),
        "source": source_label,
        "content_hash": None,
        "status": "active",
        # user submissions are inherently less trustworthy than API/scraper
        # sources — always flagged for a human to sanity-check
        "needs_manual_review": 1,
    }


@router.post("")
@limiter.limit("10/hour")
def submit_job(request: Request, body: SubmissionRequest, current_user=Depends(get_current_user)):
    if not body.url and not body.text:
        raise HTTPException(status_code=400, detail="Provide either a url or pasted text")
    if body.url and body.text:
        raise HTTPException(status_code=400, detail="Provide only one of url or text, not both")

    submission_type = "url" if body.url else "text"
    submission_value = body.url or body.text
    submission_id = create_pending_submission(submission_type, submission_value)

    extracted = None
    apply_url = None

    if body.url:
        apply_url = body.url
        try:
            resp = requests.get(body.url, headers=HEADERS, timeout=FETCH_TIMEOUT)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Couldn't fetch submitted URL {body.url}: {e}")
            update_pending_submission_status(submission_id, "failed_fetch")
            raise HTTPException(status_code=400, detail=f"Couldn't reach that URL: {e}")

        extracted = extract_job_posting(resp.text, body.url)
        if not extracted:
            # deterministic chain found nothing — try the LLM on the raw page text
            extracted = extract_with_llm(resp.text[:8000])
    else:
        # raw pasted text has no HTML to run the deterministic chain against —
        # goes straight to the LLM
        extracted = extract_with_llm(body.text)

    if not extracted:
        update_pending_submission_status(submission_id, "failed_extraction")
        raise HTTPException(
            status_code=422,
            detail="Couldn't pull job details out of that — it may not be a job posting, "
            "or the page/text didn't have enough recognizable information. "
            "It's been logged for manual review.",
        )

    listing = _build_listing(extracted, source_label="user_submission", apply_url=apply_url)

    try:
        insert_listing(listing)
    except Exception as e:
        logger.error(f"Failed to insert submitted listing: {e}")
        update_pending_submission_status(submission_id, "failed_insert")
        raise HTTPException(status_code=500, detail="Extracted the job details but couldn't save them — try again")

    update_pending_submission_status(submission_id, "added")

    return {
        "added": True,
        "extraction_method": extracted.get("extraction_method"),
        "title": listing["title"],
        "company": listing["company"],
    }
