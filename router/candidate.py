from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import JSONResponse
from router.auth import get_db,get_current_user
from models import CandidateProfile as candidateprofileModel,Users
from Pydantic.candidatePydantic import CandidateProfile as candidatepydantic
from typing import Annotated
from sqlalchemy.orm import Session

router = APIRouter()
db_dependency = Annotated[Session,Depends(get_db)]
user_dependency = Annotated[dict,Depends(get_current_user)]
@router.post("/create-user-profile/{user_id}")
def create_user_profile(db:db_dependency,user:user_dependency,prodata:candidatepydantic,user_id:int):

    # 1. Check whether the user exists in the Users table
    matchId = db.query(Users).filter(Users.id == user_id).first()

    if not matchId:
        raise HTTPException(status_code=404,detail="User does not exist")

    # 2. Check whether the user already has a candidate profile
    checkCdPr = db.query(candidateprofileModel).filter(candidateprofileModel.user_id == user_id).first()

    if checkCdPr:
        raise HTTPException(status_code=400,detail="Candidate profile already exists")

    # 3. If both checks pass, create the candidate profile
    
    candidatModel = candidateprofileModel(
        user_id= user_id,
        full_name=prodata.full_name,
        phone=prodata.phone,
        location=prodata.location,
        headline=prodata.headline,
        bio=prodata.bio,
        resume_url=prodata.resume_url,
        expected_salary = prodata.expected_salary,
        open_to_work = prodata.open_to_work

    )

    db.add(candidatModel)
    db.commit()
    return JSONResponse(status_code=201,content={'message':'Profile added successfull'})

    
