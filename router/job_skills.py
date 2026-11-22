from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from router.auth import get_db, get_current_user
from router.skill import get_or_create_skill
from models import Jobs, JobSkills, Skills, CompanyMembers
from Pydantic.skillPydantic import JobSkillCreate, JobSkillUpdate, JobSkillOut

router = APIRouter(prefix="/jobs/{job_id}/skills", tags=["Job Skills"])

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def get_job_or_404(db: Session, job_id: int) -> Jobs:
    job = db.get(Jobs, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def require_company_member(db: Session, user: dict, job: Jobs):
    member = (
        db.query(CompanyMembers)
        .filter(CompanyMembers.user_id == user.get("id"), CompanyMembers.company_id == job.company_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="Only members of this job's company can change its skills")


def to_out(row: JobSkills, skill: Skills) -> dict:
    return {"skill_id": skill.id, "name": skill.name, "is_required": row.is_required}


@router.post("", response_model=JobSkillOut, status_code=status.HTTP_201_CREATED)
def add_job_skill(db: db_dependency, user: user_dependency, job_id: int, payload: JobSkillCreate):
    job = get_job_or_404(db, job_id)
    require_company_member(db, user, job)

    skill = get_or_create_skill(db, payload.name)  # item 35: created automatically if missing

    already = db.query(JobSkills).filter(JobSkills.job_id == job_id, JobSkills.skill_id == skill.id).first()
    if already:
        raise HTTPException(status_code=409, detail="This job already has this skill")

    row = JobSkills(job_id=job_id, skill_id=skill.id, is_required=payload.is_required)
    db.add(row)
    db.commit()
    return to_out(row, skill)


@router.get("", response_model=list[JobSkillOut])
def get_job_skills(db: db_dependency, user: user_dependency, job_id: int):
    get_job_or_404(db, job_id)

    rows = (
        db.query(JobSkills, Skills)
        .join(Skills, Skills.id == JobSkills.skill_id)
        .filter(JobSkills.job_id == job_id)
        .order_by(JobSkills.is_required.desc(), Skills.name)
        .all()
    )
    return [to_out(row, skill) for row, skill in rows]


@router.put("/{skill_id}", response_model=JobSkillOut)
def update_job_skill(db: db_dependency, user: user_dependency, job_id: int, skill_id: int, payload: JobSkillUpdate):
    job = get_job_or_404(db, job_id)
    require_company_member(db, user, job)

    row = db.query(JobSkills).filter(JobSkills.job_id == job_id, JobSkills.skill_id == skill_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="This job doesn't have this skill")

    row.is_required = payload.is_required
    db.commit()
    return to_out(row, db.get(Skills, skill_id))


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_job_skill(db: db_dependency, user: user_dependency, job_id: int, skill_id: int):
    job = get_job_or_404(db, job_id)
    require_company_member(db, user, job)

    row = db.query(JobSkills).filter(JobSkills.job_id == job_id, JobSkills.skill_id == skill_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="This job doesn't have this skill")

    db.delete(row)  # removes it from this job only, the master skill stays
    db.commit()
