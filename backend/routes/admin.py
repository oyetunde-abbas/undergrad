"""
Lets a trusted local machine (wherever fetch_apis.py actually runs) push
scraped listings into this deployed backend, without needing the deployed
backend itself to have outbound internet access to job sites.

This matters specifically for free hosts like PythonAnywhere, where the
free tier restricts OUTBOUND requests from the server to a whitelist of
approved sites — but does NOT restrict INBOUND requests to your own hosted
app. So: scraping happens on a machine with full internet access (a
laptop, or any VPS), and the results get pushed in here as a normal
inbound API call.

Auth here is deliberately NOT the regular user JWT system — this endpoint
represents "a trusted machine", not "a logged-in person", so it uses a
single shared secret instead (like a webhook secret). Keep SYNC_API_KEY
private, the same way you'd treat any other secret in .env.
"""

import os
import logging

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional

from db import insert_listing, get_reported_listings, set_listing_status, expire_listings
from rate_limit import limiter

logger = logging.getLogger("admin")
router = APIRouter()

SYNC_API_KEY = os.getenv("SYNC_API_KEY")


class ListingIn(BaseModel):
    title: str
    company: Optional[str] = None
    summary: Optional[str] = None
    apply_url: Optional[str] = None
    deadline: Optional[str] = None
    location: Optional[str] = None
    remote: Optional[int] = 0
    nysc_free: Optional[int] = 0
    eligibility_notes: Optional[str] = None
    source: Optional[str] = None
    content_hash: Optional[str] = None
    status: Optional[str] = "active"
    needs_manual_review: Optional[int] = 0
    work_style: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
    skills: Optional[str] = None
    experience_level: Optional[str] = None
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None
    expires_at: Optional[str] = None


class SyncRequest(BaseModel):
    listings: List[ListingIn]


def _check_sync_key(x_sync_key: Optional[str]):
    if not SYNC_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Sync isn't configured on this server — set SYNC_API_KEY in .env first.",
        )
    if not x_sync_key or x_sync_key != SYNC_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing sync key")


@router.post("/sync-listings")
@limiter.limit("10/hour")
def sync_listings(request: Request, body: SyncRequest, x_sync_key: Optional[str] = Header(default=None)):
    _check_sync_key(x_sync_key)

    inserted = 0
    failed = 0
    for listing in body.listings:
        try:
            insert_listing(listing.dict(), from_sync=True)
            inserted += 1
        except Exception as e:
            failed += 1
            logger.error(f"Failed to sync listing '{listing.title}': {e}")

    logger.info(f"Sync complete: {inserted} processed, {failed} failed")
    return {"processed": inserted, "failed": failed}



class StatusChange(BaseModel):
    status: str  # active (restore) | closed (remove) | expired


@router.get("/reported-listings")
def reported_listings(x_sync_key: Optional[str] = Header(default=None)):
    _check_sync_key(x_sync_key)
    return {"listings": get_reported_listings()}


@router.post("/listings/{listing_id}/status")
def change_listing_status(listing_id: int, body: StatusChange, x_sync_key: Optional[str] = Header(default=None)):
    _check_sync_key(x_sync_key)
    try:
        ok = set_listing_status(listing_id, body.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
    if not ok:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"updated": True}


@router.post("/expire-sweep")
def expire_sweep(x_sync_key: Optional[str] = Header(default=None)):
    """Cron-friendly: flips past-expiry listings to 'expired'. The feed hides them
    by time regardless; this just keeps the status column honest."""
    _check_sync_key(x_sync_key)
    return {"expired": expire_listings()}
