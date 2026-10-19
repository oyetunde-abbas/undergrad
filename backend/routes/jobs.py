from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

import onboarding
from deps import get_current_user
from rate_limit import limiter

from db import (
    get_job,
    get_jobs,
    count_jobs,
    get_sources,
    get_locations,
    report_listing,
    get_profile,
)


router=APIRouter()



@router.get("")
def read_jobs(

    page:int=Query(1,ge=1),

    limit:int=Query(20,ge=1,le=50),

    search:str="",

    remote:Optional[bool]=None,

    work_style:str="",

    job_type:str="",

    category:str="",

    skill:str="",

    location:str="",

    sort:str="newest",

    nysc:str="",

    my_degree:str=""

):


    remote_value=None


    if remote is not None:

        remote_value=1 if remote else 0



    jobs=get_jobs(

        page=page,

        limit=limit,

        search=search,

        remote=remote_value,

        work_style=work_style,

        job_type=job_type,

        category=category,

        skill=skill,

        location=location,

        sort=sort,

        nysc=nysc,

        my_degree=my_degree

    )



    total=count_jobs(

        search=search,

        remote=remote_value,

        work_style=work_style,

        job_type=job_type,

        category=category,

        skill=skill,

        location=location,

        nysc=nysc,

        my_degree=my_degree

    )


    return {

        "page":page,

        "limit":limit,

        "total":total,

        "jobs":jobs

    }





@router.get("/for-you")
def jobs_for_you(limit: int = Query(10, ge=1, le=30), current_user=Depends(get_current_user)):
    """Live listings ranked by the student's onboarding answers, each with plain-language reasons."""
    profile = get_profile(current_user["id"]) or {}
    prefs = profile.get("onboarding") or {}
    if not prefs or prefs.get("skipped"):
        return {"personalised": False, "jobs": []}
    return {"personalised": True, "jobs": onboarding.rank_for_you(get_jobs, prefs, limit=limit)}


@router.get("/sources")
def sources():

    return get_sources()



@router.get("/locations")
def locations():

    return get_locations()




@router.get("/{job_id}")
def job(job_id:int):

    result=get_job(job_id)


    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )


    return result



class ReportBody(BaseModel):
    reason: Optional[str] = None


@router.post("/{job_id}/report")
@limiter.limit("20/hour")
def report_job(request: Request, job_id: int, body: ReportBody, current_user=Depends(get_current_user)):
    """User flags a listing (scam, fee requested, already closed...). One report
    per user per listing; enough distinct reports hides it pending review."""
    result = report_listing(current_user["id"], job_id, body.reason)
    if not result["found"]:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "reported": True,
        "already_reported": not result["new_report"],
        "hidden": result["hidden"],
    }
