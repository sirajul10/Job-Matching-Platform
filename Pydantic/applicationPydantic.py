from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal
from datetime import datetime



class ApplicationCreate(BaseModel):
    job_id: int
    resume_url: Optional[str] = None
    cover_letter: Optional[str] = None



class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    candidate_id: int
    resume_url: Optional[str] = None
    cover_letter: Optional[str] = None
    status: str
    applied_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationStatusUpdate(BaseModel):
    status: Literal[
        "reviewed",
        "shortlisted",
        "interview",
        "rejected",
        "hired",
        "withdrawn"
    ]
    note: Optional[str] = None


class ApplicationStatusHistoryResponse(BaseModel):
    id: int
    application_id: int
    changed_by: Optional[int] = None
    old_status: Optional[str] = None
    new_status: str
    note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationTimelineEvent(BaseModel):
    status: str
    changed_by: Optional[int] = None
    note: Optional[str] = None
    created_at: datetime


class ApplicationTimelineResponse(BaseModel):
    application_id: int
    job_id: int
    current_status: str
    timeline: list[ApplicationTimelineEvent]

class ApplicationActionRequest(BaseModel):
    note: Optional[str] = None



class ApplicationCommentCreate(BaseModel):
    comment: str


class ApplicationCommentResponse(BaseModel):
    id: int
    application_id: int
    user_id: Optional[int] = None
    comment: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



class ApplicationDocumentCreate(BaseModel):
    document_name: str
    document_url: str
    document_type: Optional[str] = None


class ApplicationDocumentResponse(BaseModel):
    id: int
    application_id: int
    uploaded_by: Optional[int] = None
    document_name: str
    document_url: str
    document_type: Optional[str] = None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)
