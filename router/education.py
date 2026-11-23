
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from router.auth import get_db, get_current_user
from models import Education, CandidateProfile
from Pydantic.educationPydantic import (
    EducationCreate,
    EducationUpdate,
    OngoingEducation,
    EducationResponse,
)

router = APIRouter(tags=["Education"])
db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def get_candidate(db: Session, user: dict):
    candidate = db.query(CandidateProfile).filter(
        CandidateProfile.user_id == user.get('id')
    ).first()

    if candidate is None:
        raise HTTPException(status_code=404, detail='Candidate profile not found. Create profile first')

    return candidate


# 19. Add Education
@router.post('/add-education')
def add_education(user: user_dependency, db: db_dependency, eddata: EducationCreate):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    candidate = get_candidate(db, user)

    education_model = Education(
        candidate_id=candidate.id,
        institution=eddata.institution,
        degree=eddata.degree,
        field_of_study=eddata.field_of_study,
        start_date=eddata.start_date,
        end_date=eddata.end_date,
        still_running=eddata.still_running,
        grade=eddata.grade,
        description=eddata.description
    )

    db.add(education_model)
    db.commit()

    return JSONResponse(status_code=201, content={'message': 'Education added successfully'})


# 20. Get Education (all)
@router.get('/get-education', response_model=list[EducationResponse])
def get_education(user: user_dependency, db: db_dependency):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    candidate = get_candidate(db, user)

    educations = (
        db.query(Education)
        .filter(Education.candidate_id == candidate.id)
        .order_by(Education.start_date.desc())
        .all()
    )

    return educations


# 20. Get Education (single)
@router.get('/get-education/{education_id}', response_model=EducationResponse)
def get_single_education(user: user_dependency, db: db_dependency, education_id: int):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    candidate = get_candidate(db, user)

    education = (
        db.query(Education)
        .filter(Education.id == education_id)
        .filter(Education.candidate_id == candidate.id)
        .first()
    )

    if education is None:
        raise HTTPException(status_code=404, detail='Education not found')

    return education


# 21. Update Education
@router.put('/update-education/{education_id}')
def update_education(user: user_dependency, db: db_dependency, eddata: EducationUpdate, education_id: int):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    candidate = get_candidate(db, user)

    education = (
        db.query(Education)
        .filter(Education.id == education_id)
        .filter(Education.candidate_id == candidate.id)
        .first()
    )

    if education is None:
        raise HTTPException(status_code=404, detail='Education not found')

    updates = eddata.model_dump(exclude_unset=True)

    for key, value in updates.items():
        setattr(education, key, value)

    # Ongoing education rule
    if education.still_running:
        education.end_date = None
    else:
        if education.end_date is None:
            raise HTTPException(status_code=400, detail='end_date is required when education is completed')

        if education.end_date < education.start_date:
            raise HTTPException(status_code=400, detail='end_date cannot be before start_date')

    db.commit()

    return JSONResponse(status_code=200, content={'message': 'Education updated successfully'})


# 22. Delete Education
@router.delete('/delete-education/{education_id}')
def delete_education(user: user_dependency, db: db_dependency, education_id: int):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    candidate = get_candidate(db, user)

    education = (
        db.query(Education)
        .filter(Education.id == education_id)
        .filter(Education.candidate_id == candidate.id)
        .first()
    )

    if education is None:
        raise HTTPException(status_code=404, detail='Education not found')

    db.delete(education)
    db.commit()

    return JSONResponse(status_code=200, content={'message': 'Education deleted successfully'})


# 23. Ongoing Education Management
@router.put('/ongoing-education/{education_id}')
def manage_ongoing_education(user: user_dependency, db: db_dependency, eddata: OngoingEducation, education_id: int):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    candidate = get_candidate(db, user)

    education = (
        db.query(Education)
        .filter(Education.id == education_id)
        .filter(Education.candidate_id == candidate.id)
        .first()
    )

    if education is None:
        raise HTTPException(status_code=404, detail='Education not found')

    if eddata.still_running:
        education.still_running = True
        education.end_date = None
    else:
        if eddata.end_date is None:
            raise HTTPException(status_code=400, detail='end_date is required when education is completed')

        if eddata.end_date < education.start_date:
            raise HTTPException(status_code=400, detail='end_date cannot be before start_date')

        education.still_running = False
        education.end_date = eddata.end_date

    db.commit()

    return JSONResponse(status_code=200, content={'message': 'Ongoing education updated successfully'})
