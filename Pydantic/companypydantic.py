from pydantic import BaseModel,Field,HttpUrl,ConfigDict
from typing import Optional

class CompanyPydantic(BaseModel):

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    name: str = Field( ...,min_length=5,max_length=100,description="Company full name.")
    description:str = Field(default=None,max_length=1000,description="Brief  summary of the company.")
    website:str = Field(default=None,max_length=500,description="Company website.")
    logo_url:str = Field(default=None,max_length=500,description="Company Logo.")
    industry:str = Field(default=None,max_length=150,description="Company Logo.")
    size:int 
    location:str = Field(default=None,max_length=200,description="Company Location.")