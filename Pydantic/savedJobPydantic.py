from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SavedJobOut(BaseModel):
    job_id: int
    title: str
    company_id: int
    company_name: str
    location: Optional[str]
    is_remote: bool
    job_type: str
    experience_level: Optional[str]
    salary_min: Optional[float]
    salary_max: Optional[float]
    currency: Optional[str]
    status: str                      # "closed" tells the candidate it no longer accepts applications
    expires_at: Optional[datetime]
    saved_at: datetime
