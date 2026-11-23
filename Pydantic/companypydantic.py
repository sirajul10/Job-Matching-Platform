from pydantic import BaseModel,Field,HttpUrl,ConfigDict
from datetime import datetime
from typing import Optional

class CompanyPydantic(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )

    name: str = Field(..., min_length=5, max_length=100, description="Company full name.")
    description: Optional[str] = Field(default=None, max_length=1000, description="Brief summary of the company.")
    website: Optional[str] = Field(default=None, max_length=500, description="Company website.")
    logo_url: Optional[str] = Field(default=None, max_length=500, description="Company logo URL.")
    industry: Optional[str] = Field(default=None, max_length=150, description="Company industry.")
    size: Optional[int] = Field(default=None, ge=1, description="Number of employees.")
    location: Optional[str] = Field(default=None, max_length=200, description="Company location.")



class UpdateCompanyPy(BaseModel):

    model_config = ConfigDict(str_strip_whitespace=True,validate_assignment=True,extra="forbid")
    name: Optional[str] = Field(default=None,min_length=5,max_length=100,description="Company full name.")
    description: Optional[str] = Field(default=None,max_length=1000,description="Brief summary of the company.")
    website: Optional[str] = Field(default=None,max_length=500,description="Company website.")
    logo_url: Optional[str] = Field(default=None,max_length=500,description="Company logo URL.")
    industry: Optional[str] = Field(default=None,max_length=150,description="Company industry.")
    size: Optional[int] = Field(default=None,ge=1,description="Number of employees.")
    location: Optional[str] = Field(default=None,max_length=200,description="Company location." )


class Cmpmember(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    user_id:int
    role: str

class UpdateRole(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    role: str

class Jobdata(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    title:str = Field(default=None,min_length=5,max_length=100,description="Job Title.")
    description:str = Field(default=None, max_length=1000, description="Brief summary of the company.")
    requirements:str = Field(default=None, max_length=1000, description="requirements summary.")
    responsibilities:str = Field(default=None, max_length=1000, description="responsibilities summary.")
    location:str = Field(default=None, max_length=200, description="Company location.")
    is_remote:bool = Field(default=True,description="Remote job or in Present.")
    job_type:str = Field(default=None,min_length=5,max_length=100,description="full-time / part-time / contract / internship")
    experience_level:str = Field(default=None,min_length=5,max_length=100,description="entry / junior / mid / senior")
    salary_min:float 
    salary_max:float
    status:str = Field(default=None,min_length=5,max_length=100,description="draft / open / closed.")
    expires_at: Optional[datetime] = Field(default=None,description="Job expiration date and time")