from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel

from db import get_profile, update_profile, set_resume, clear_resume
from deps import get_current_user

router = APIRouter()

RESUME_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "resumes"
RESUME_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}
MAX_RESUME_BYTES = 5 * 1024 * 1024  # 5MB


class ProfileUpdate(BaseModel):
    about: Optional[str] = None
    skills: Optional[List[str]] = None


@router.get("")
def read_profile(current_user=Depends(get_current_user)):
    return get_profile(current_user["id"])


@router.patch("")
def edit_profile(body: ProfileUpdate, current_user=Depends(get_current_user)):
    return update_profile(current_user["id"], about=body.about, skills=body.skills)


def _resume_stored_filename(user_id, ext):
    # per-user filename so two users' resumes never collide on disk
    return f"resume_user{user_id}{ext}"


def _existing_resume_path(profile):
    if profile and profile.get("resume_filename"):
        p = RESUME_DIR / profile["resume_filename"]
        if p.exists():
            return p
    return None


@router.post("/resume")
async def upload_resume(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    original_name = file.filename or "resume"
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    contents = await file.read()
    if len(contents) > MAX_RESUME_BYTES:
        raise HTTPException(status_code=400, detail="File too large — 5MB limit.")
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="File is empty.")

    old_profile = get_profile(current_user["id"])
    old_path = _existing_resume_path(old_profile)
    if old_path:
        old_path.unlink(missing_ok=True)

    stored_filename = _resume_stored_filename(current_user["id"], ext)
    dest = RESUME_DIR / stored_filename
    dest.write_bytes(contents)

    return set_resume(current_user["id"], stored_filename, original_name)


@router.get("/resume")
def download_resume(current_user=Depends(get_current_user)):
    profile = get_profile(current_user["id"])
    path = _existing_resume_path(profile)
    if not path:
        raise HTTPException(status_code=404, detail="No resume uploaded")
    display_name = profile.get("resume_original_name") or path.name
    return FileResponse(path, filename=display_name)


@router.delete("/resume")
def delete_resume(current_user=Depends(get_current_user)):
    profile = get_profile(current_user["id"])
    path = _existing_resume_path(profile)
    if not path:
        raise HTTPException(status_code=404, detail="No resume uploaded")
    path.unlink(missing_ok=True)
    return clear_resume(current_user["id"])
