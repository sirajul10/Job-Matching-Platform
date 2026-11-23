
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


class EducationCreate(BaseModel):
    institution: str = Field(min_length=1, max_length=200)
    degree: str = Field(min_length=1, max_length=100)
    field_of_study: str = Field(min_length=1, max_length=150)
    start_date: date
    end_date: Optional[date] = None
    still_running: bool = False
    grade: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None

    @model_validator(mode="after")
    def check_dates(self):
        if self.still_running:
            self.end_date = None
        else:
            if self.end_date is None:
                raise ValueError("end_date is required when education is completed")
            if self.end_date < self.start_date:
                raise ValueError("end_date cannot be before start_date")
        return self


class EducationUpdate(BaseModel):
    institution: Optional[str] = Field(default=None, min_length=1, max_length=200)
    degree: Optional[str] = Field(default=None, min_length=1, max_length=100)
    field_of_study: Optional[str] = Field(default=None, min_length=1, max_length=150)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    still_running: Optional[bool] = None
    grade: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None


class OngoingEducation(BaseModel):
    still_running: bool
    end_date: Optional[date] = None


class EducationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    institution: str
    degree: str
    field_of_study: str
    start_date: date
    end_date: Optional[date] = None
    still_running: bool
    grade: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
