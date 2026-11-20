from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import JSONResponse
from router.auth import get_db,get_current_user
from models import CandidateProfile as candidateprofileModel,Users
from Pydantic.candidatePydantic import CandidateProfile as candidatepydantic
from Pydantic.candidatePydantic import updatepropydantic
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

    
@router.get("/candidate/{user_id}")
def get_user(user:user_dependency,db:db_dependency,user_id:int):

    id = user.get('id')
    if id != user_id:
        raise HTTPException(status_code=401,detail="Please Login First")
    candidate = db.query(candidateprofileModel).filter(candidateprofileModel.user_id == user_id).first()
    
   
    if candidate is None:
        raise HTTPException(status_code=401,detail="Please Complete Yoyr Profile")

    return candidate


@router.put("/update-profile/{user_id}")
def update_profile(db:db_dependency,user:user_dependency,uppro:updatepropydantic,user_id:int):

    id = user.get('id')
    if id != user_id:
        raise HTTPException(status_code=401,detail="Please Login First")

    candidaeProfile = db.query(candidateprofileModel).filter(candidateprofileModel.user_id == user_id).first()

    if candidaeProfile is None:
        raise HTTPException(status_code=401,detail="Please Create Profile First")

    update_profile = uppro.model_dump(exclude_unset=True)
    for key,val in update_profile.items():
        setattr(candidaeProfile,key,val)

    db.commit()

    return JSONResponse(status_code=200,content={'message':'Profile Update successfull'})


@router.delete("/delete-profile/{user_id}")
def delete_profile(db:db_dependency,user:user_dependency,user_id:int):

    id = user.get('id')
    if id != user_id:
        raise HTTPException(status_code=401,detail="Please Login First")

    candidaeProfile = db.query(candidateprofileModel).filter(candidateprofileModel.user_id == user_id).first()

    if candidaeProfile is None:
        raise HTTPException(status_code=401,detail="I am unable to find your profile")

    fullname = candidaeProfile.full_name

    db.delete(candidaeProfile)
    db.commit()

    return JSONResponse(status_code=202,content={'message':f'{fullname } your profile hase deleted'})



    