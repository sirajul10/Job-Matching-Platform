from datetime import datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

JobType = Literal["full-time", "part-time", "contract", "internship"]
ExperienceLevel = Literal["entry", "junior", "mid", "senior"]
SkillName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class JobAlertBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: Optional[str] = Field(default=None, max_length=100, description="Label, e.g. Remote Python jobs")
    keyword: Optional[str] = Field(default=None, min_length=2, max_length=100)
    location: Optional[str] = Field(default=None, min_length=2, max_length=200)
    is_remote: Optional[bool] = None
    job_type: Optional[JobType] = None
    experience_level: Optional[ExperienceLevel] = None
    min_salary: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, pattern=r"^[A-Za-z]{3}$", description="3-letter code, e.g. USD")

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v):
        return v.upper() if v else v


class JobAlertCreate(JobAlertBase):
    skills: list[SkillName] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def check_preferences(self):
        has_filter = any([
            self.keyword, self.location, self.is_remote is not None, self.job_type,
            self.experience_level, self.min_salary is not None, self.skills,
        ])
        if not has_filter:
            raise ValueError("Add at least one search preference to the alert")
        if self.min_salary is not None and not self.currency:
            raise ValueError("currency is required when min_salary is given")
        return self


class JobAlertUpdate(JobAlertBase):
    """Only the fields you send are changed. Send null to clear a filter, skills: [] to clear skills."""

    skills: Optional[list[SkillName]] = Field(default=None, max_length=10)
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def is_active_not_null(self):
        if "is_active" in self.model_fields_set and self.is_active is None:
            raise ValueError("is_active cannot be null")
        return self


class JobAlertOut(BaseModel):
    id: int
    name: Optional[str]
    keyword: Optional[str]
    location: Optional[str]
    is_remote: Optional[bool]
    job_type: Optional[str]
    experience_level: Optional[str]
    min_salary: Optional[float]
    currency: Optional[str]
    skills: list[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
