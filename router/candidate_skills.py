from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from router.auth import get_db, get_current_user
from router.skill import get_or_create_skill
from models import CandidateProfile, CandidateSkills, Skills
from Pydantic.skillPydantic import CandidateSkillCreate, CandidateSkillUpdate, CandidateSkillOut

# "/candidates/me/skills" (plural) on purpose: candidate.py already has "/candidate/{user_id}"
router = APIRouter(prefix="/candidates/me/skills", tags=["Candidate Skills"])

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def get_my_profile(db: Session, user: dict) -> CandidateProfile:
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user.get("id")).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Please create your candidate profile first")
    return profile


def to_out(row: CandidateSkills, skill: Skills) -> dict:
    return {"skill_id": skill.id, "name": skill.name, "years_of_experience": row.years_of_experience}


@router.post("", response_model=CandidateSkillOut, status_code=status.HTTP_201_CREATED)
def add_my_skill(db: db_dependency, user: user_dependency, payload: CandidateSkillCreate):
    profile = get_my_profile(db, user)

    skill = get_or_create_skill(db, payload.name)  # item 35: created automatically if missing

    already = (
        db.query(CandidateSkills)
        .filter(CandidateSkills.candidate_id == profile.id, CandidateSkills.skill_id == skill.id)
        .first()
    )
    if already:
        raise HTTPException(status_code=409, detail="You already have this skill")

    row = CandidateSkills(
        candidate_id=profile.id,
        skill_id=skill.id,
        years_of_experience=payload.years_of_experience,
    )
    db.add(row)
    db.commit()
    return to_out(row, skill)


@router.get("", response_model=list[CandidateSkillOut])
def get_my_skills(db: db_dependency, user: user_dependency):
    profile = get_my_profile(db, user)

    rows = (
        db.query(CandidateSkills, Skills)
        .join(Skills, Skills.id == CandidateSkills.skill_id)
        .filter(CandidateSkills.candidate_id == profile.id)
        .order_by(Skills.name)
        .all()
    )
    return [to_out(row, skill) for row, skill in rows]


@router.put("/{skill_id}", response_model=CandidateSkillOut)
def update_my_skill(db: db_dependency, user: user_dependency, skill_id: int, payload: CandidateSkillUpdate):
    profile = get_my_profile(db, user)

    row = (
        db.query(CandidateSkills)
        .filter(CandidateSkills.candidate_id == profile.id, CandidateSkills.skill_id == skill_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="You don't have this skill")

    row.years_of_experience = payload.years_of_experience
    db.commit()
    return to_out(row, db.get(Skills, skill_id))


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_my_skill(db: db_dependency, user: user_dependency, skill_id: int):
    profile = get_my_profile(db, user)

    row = (
        db.query(CandidateSkills)
        .filter(CandidateSkills.candidate_id == profile.id, CandidateSkills.skill_id == skill_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="You don't have this skill")

    db.delete(row)  # removes it from your profile only, the master skill stays
    db.commit()
