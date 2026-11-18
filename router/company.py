from Pydantic.companypydantic import CompanyPydantic
from models import Companies,Users,CandidateProfile
from router.auth import get_current_user,get_db
from typing import Annotated
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

router = APIRouter()
db_dependency = Annotated[Session,Depends(get_db)]
user_dependency = Annotated[dict,Depends(get_current_user)] 

