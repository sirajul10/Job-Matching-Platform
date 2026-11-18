
from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from typing import Optional


class CandidateProfile(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Candidate's full legal name."
    )

    phone: str = Field(
        ...,
        min_length=8,
        max_length=20,
        description="Candidate's contact phone number."
    )

    location: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Candidate's current city or location."
    )

    headline: str = Field(
        ...,
        min_length=5,
        max_length=150,
        description="Professional headline or current job title."
    )

    bio: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Brief professional summary of the candidate."
    )

    resume_url: Optional[HttpUrl] = Field(
    default=None,
    description="URL pointing to the candidate's resume."
   )

    expected_salary: Optional[float] = Field(
        default=None,
        ge=100,
        description="Candidate's expected minimum salary."
    )

    open_to_work: bool = Field(
        default=True,
        description="Indicates whether the candidate is currently open to job opportunities."
    )
