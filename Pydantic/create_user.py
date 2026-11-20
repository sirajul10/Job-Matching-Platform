import re
from pydantic import BaseModel, EmailStr, Field, field_validator,model_validator


class CreateUsers(BaseModel):
    username: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[^\w\s]", v):
            raise ValueError("Password must contain at least one special character")
        return v

class Updateuser(BaseModel):
    pass

class PasswodChange(BaseModel):
    old_password: str
    newpassword: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("newpassword")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[^\w\s]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.newpassword != self.confirm_password:
            raise ValueError("New password and confirm password do not match")
        return self


class forgotPassPydantic(BaseModel):
    username:str
    newpassword: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    
    @field_validator("newpassword")
    @classmethod
    def password_strength(cls,v:str)->str:
        if not re.search(r"\d",v):
            raise ValueError("password must containt atleast one number")
        return v
    @model_validator(mode="after")
    def check_password_match(self):
        if self.newpassword != self.confirm_password:
            raise ValueError("New password and confirm password do not match")
        return self
        