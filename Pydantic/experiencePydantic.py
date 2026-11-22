from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


class ExperienceCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=150)
    employment_type: Optional[str] = Field(default=None, max_length=50)  # Full-time / Part-time / Internship / Contract
    location: Optional[str] = Field(default=None, max_length=150)
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    still_running: bool = False

    @model_validator(mode="after")
    def check_dates(self):
        # Current employment: end_date must be NULL
        if self.still_running:
            self.end_date = None
        else:
            if self.end_date is None:
                raise ValueError("end_date is required when still_running is false")
            if self.end_date < self.start_date:
                raise ValueError("end_date cannot be before start_date")
        return self


class ExperienceUpdate(BaseModel):
    company_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    employment_type: Optional[str] = Field(default=None, max_length=50)
    location: Optional[str] = Field(default=None, max_length=150)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    still_running: Optional[bool] = None


class CurrentEmployment(BaseModel):
    still_running: bool
    end_date: Optional[date] = None  # lagbe jodi still_running = False hoy


class ExperienceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    company_name: str
    title: str
    employment_type: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    still_running: bool
    created_at: datetime
    updated_at: Optional[datetime] = None