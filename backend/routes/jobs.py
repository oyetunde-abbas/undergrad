from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from db import get_job, get_jobs

router = APIRouter()


@router.get("")
def read_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    search: str = "",
    remote: Optional[bool] = None,
    source: str = "",
    location: str = "",
):

    remote_value = None

    if remote is not None:
        remote_value = 1 if remote else 0

    return get_jobs(
        page=page,
        limit=limit,
        search=search,
        remote=remote_value,
        source=source,
        location=location,
    )


@router.get("/{job_id}")
def read_job(job_id: int):

    job = get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    return job