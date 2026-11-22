from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from router.auth import get_db, get_current_user
from models import Experience, CandidateProfile
from Pydantic.experiencePydantic import (
    ExperienceCreate,
    ExperienceUpdate,
    CurrentEmployment,
    ExperienceResponse,
)

router = APIRouter()
db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def get_candidate(db: Session, user: dict):
    candidate = db.query(CandidateProfile).filter(CandidateProfile.user_id == user.get('id')).first()
    if candidate is None:
        raise HTTPException(status_code=404, detail='Candidate profile not found. Create profile first')
    return candidate


# 24. Add Experience
@router.post('/add-experience')
def add_experience(user: user_dependency, db: db_dependency, exdata: ExperienceCreate):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    candidate = get_candidate(db, user)

    experience_model = Experience(
        candidate_id=candidate.id,
        company_name=exdata.company_name,
        title=exdata.title,
        employment_type=exdata.employment_type,
        location=exdata.location,
        description=exdata.description,
        start_date=exdata.start_date,
        end_date=exdata.end_date,
        still_running=exdata.still_running
    )

    db.add(experience_model)
    db.commit()
    return JSONResponse(status_code=201, content={'message': 'Experience added successfully'})


# 25. Get Experience (all)
@router.get('/get-experience', response_model=list[ExperienceResponse])
def get_experience(user: user_dependency, db: db_dependency):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    candidate = get_candidate(db, user)

    experiences = (
        db.query(Experience)
        .filter(Experience.candidate_id == candidate.id)
        .order_by(Experience.start_date.desc())
        .all()
    )
    return experiences


# 25. Get Experience (single)
@router.get('/get-experience/{experience_id}', response_model=ExperienceResponse)
def get_single_experience(user: user_dependency, db: db_dependency, experience_id: int):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    candidate = get_candidate(db, user)

    experience = db.query(Experience).filter(Experience.id == experience_id).filter(Experience.candidate_id == candidate.id).first()
    if experience is None:
        raise HTTPException(status_code=404, detail='Experience not found')

    return experience


# 26. Update Experience
@router.put('/update-experience/{experience_id}')
def update_experience(user: user_dependency, db: db_dependency, exdata: ExperienceUpdate, experience_id: int):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    candidate = get_candidate(db, user)

    experience = db.query(Experience).filter(Experience.id == experience_id).filter(Experience.candidate_id == candidate.id).first()
    if experience is None:
        raise HTTPException(status_code=404, detail='Experience not found')

    # Shudhu jegulo pathano hoyeche segulo update hobe
    updates = exdata.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(experience, key, value)

    # Current employment rule: still_running = true hole end_date = NULL
    if experience.still_running:
        experience.end_date = None
    else:
        if experience.end_date is None:
            raise HTTPException(status_code=400, detail='end_date is required when still_running is false')
        if experience.end_date < experience.start_date:
            raise HTTPException(status_code=400, detail='end_date cannot be before start_date')

    db.commit()
    return JSONResponse(status_code=200, content={'message': 'Experience updated successfully'})


# 27. Delete Experience
@router.delete('/delete-experience/{experience_id}')
def delete_experience(user: user_dependency, db: db_dependency, experience_id: int):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    candidate = get_candidate(db, user)

    experience = db.query(Experience).filter(Experience.id == experience_id).filter(Experience.candidate_id == candidate.id).first()
    if experience is None:
        raise HTTPException(status_code=404, detail='Experience not found')

    db.query(Experience).filter(Experience.candidate_id == candidate.id).filter(Experience.id == experience_id).delete()

    db.commit()
    return JSONResponse(status_code=200, content={'message': 'Experience deleted successfully'})


# 28. Current Employment Management
@router.put('/current-employment/{experience_id}')
def manage_current_employment(user: user_dependency, db: db_dependency, cdata: CurrentEmployment, experience_id: int):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    candidate = get_candidate(db, user)

    experience = db.query(Experience).filter(Experience.id == experience_id).filter(Experience.candidate_id == candidate.id).first()
    if experience is None:
        raise HTTPException(status_code=404, detail='Experience not found')

    if cdata.still_running:
        # Employment ongoing: end_date = NULL, still_running = true
        experience.still_running = True
        experience.end_date = None
    else:
        # Job sesh hoyeche: end_date dite hobe
        if cdata.end_date is None:
            raise HTTPException(status_code=400, detail='end_date is required when employment has ended')
        if cdata.end_date < experience.start_date:
            raise HTTPException(status_code=400, detail='end_date cannot be before start_date')
        experience.still_running = False
        experience.end_date = cdata.end_date

    db.commit()
    return JSONResponse(status_code=200, content={'message': 'Current employment updated successfully'})