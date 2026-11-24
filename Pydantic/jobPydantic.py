from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from Pydantic.skillPydantic import JobSkillCreate, JobSkillOut

JobType = Literal["full-time", "part-time", "contract", "internship"]
ExperienceLevel = Literal["entry", "junior", "mid", "senior"]


class JobBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=10000)
    requirements: Optional[str] = Field(default=None, max_length=5000)
    responsibilities: Optional[str] = Field(default=None, max_length=5000)

    location: Optional[str] = Field(default=None, max_length=200)
    is_remote: bool = False
    job_type: JobType
    experience_level: Optional[ExperienceLevel] = None

    salary_min: Optional[float] = Field(default=None, ge=0)
    salary_max: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, pattern=r"^[A-Za-z]{3}$", description="3-letter code, e.g. USD")

    expires_at: Optional[datetime] = Field(default=None, description="Closing date, must be in the future")

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v):
        return v.upper() if v else v

    @field_validator("expires_at")
    @classmethod
    def must_be_in_future(cls, v):
        if v is None:
            return v
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= datetime.now(timezone.utc):
            raise ValueError("expires_at must be in the future")
        return v

    @model_validator(mode="after")
    def salary_range_is_valid(self):
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            raise ValueError("salary_min cannot be greater than salary_max")
        return self


class JobCreate(JobBase):
    company_id: int
    status: Literal["draft", "open"] = Field(default="draft", description="'open' publishes the job right away")
    skills: list[JobSkillCreate] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def salary_needs_currency(self):
        if (self.salary_min is not None or self.salary_max is not None) and not self.currency:
            raise ValueError("currency is required when a salary is given")
        return self


class JobUpdate(JobBase):
    """Every field is optional: only the fields you send are changed."""

    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10, max_length=10000)
    is_remote: Optional[bool] = None
    job_type: Optional[JobType] = None

    @model_validator(mode="after")
    def required_fields_not_null(self):
        for name in ("title", "description", "job_type", "is_remote"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class JobOut(BaseModel):
    id: int
    company_id: int
    company_name: str
    posted_by: Optional[int]
    status: str

    title: str
    description: str
    requirements: Optional[str]
    responsibilities: Optional[str]
    location: Optional[str]
    is_remote: bool
    job_type: str
    experience_level: Optional[str]
    salary_min: Optional[float]
    salary_max: Optional[float]
    currency: Optional[str]

    posted_at: datetime
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    skills: list[JobSkillOut]


class JobActionResult(BaseModel):
    message: str
    action: str
