from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_applications, add_application, update_application, delete_application
from deps import get_current_user

router = APIRouter()


class ApplicationCreate(BaseModel):
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = "Applied"
    applied_date: Optional[str] = None
    notes: Optional[str] = None
    listing_id: Optional[int] = None


class ApplicationUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    applied_date: Optional[str] = None
    notes: Optional[str] = None


@router.get("")
def read_applications(current_user=Depends(get_current_user)):
    return {"applications": get_applications(current_user["id"])}


@router.post("")
def create_application(body: ApplicationCreate, current_user=Depends(get_current_user)):
    new_id = add_application(current_user["id"], body.dict())
    return {"id": new_id}


@router.patch("/{app_id}")
def edit_application(app_id: int, body: ApplicationUpdate, current_user=Depends(get_current_user)):
    updated = update_application(current_user["id"], app_id, body.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"updated": True}


@router.delete("/{app_id}")
def remove_application(app_id: int, current_user=Depends(get_current_user)):
    deleted = delete_application(current_user["id"], app_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"deleted": True}
