from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from db import (
    get_job,
    get_jobs,
    count_jobs,
    get_sources,
    get_locations
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

    sort:str="newest"

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

        sort=sort

    )



    total=count_jobs(

        search=search,

        remote=remote_value,

        work_style=work_style,

        job_type=job_type,

        category=category,

        skill=skill,

        location=location

    )


    return {

        "page":page,

        "limit":limit,

        "total":total,

        "jobs":jobs

    }





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