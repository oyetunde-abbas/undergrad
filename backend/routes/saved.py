from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_saved_jobs, save_job, unsave_job
from deps import get_current_user

router = APIRouter()


class SaveRequest(BaseModel):
    listing_id: int


@router.get("")
def read_saved(current_user=Depends(get_current_user)):
    return {"saved": get_saved_jobs(current_user["id"])}


@router.post("")
def create_saved(body: SaveRequest, current_user=Depends(get_current_user)):
    save_job(current_user["id"], body.listing_id)
    return {"saved": True, "listing_id": body.listing_id}


@router.delete("/{listing_id}")
def delete_saved(listing_id: int, current_user=Depends(get_current_user)):
    deleted = unsave_job(current_user["id"], listing_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Not found in saved jobs")
    return {"deleted": True, "listing_id": listing_id}
