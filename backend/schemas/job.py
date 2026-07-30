from pydantic import BaseModel
from typing import Optional


class Job(BaseModel):

    id: int
    title: str
    company: Optional[str]
    summary: Optional[str]
    apply_url: str
    location: Optional[str]
    remote: int
    source: str