from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from router.auth import get_db, get_current_user
from router.candidate_skills import get_my_profile
from models import SavedJobs, Jobs, Companies
from Pydantic.savedJobPydantic import SavedJobOut

router = APIRouter(prefix="/saved-jobs", tags=["Saved Jobs"])

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

PUBLIC_STATUSES = ("open", "closed")  # drafts and archived jobs are not visible to candidates


def to_out(saved: SavedJobs, job: Jobs, company: Companies) -> dict:
    return {
        "job_id": job.id,
        "title": job.title,
        "company_id": company.id,
        "company_name": company.name,
        "location": job.location,
        "is_remote": job.is_remote,
        "job_type": job.job_type,
        "experience_level": job.experience_level,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "currency": job.currency,
        "status": job.status,
        "expires_at": job.expires_at,
        "saved_at": saved.created_at,
    }


# ---------------------------------------------------------------------------
# Item 112: save a job
# ---------------------------------------------------------------------------

@router.post("/{job_id}", response_model=SavedJobOut, status_code=status.HTTP_201_CREATED)
def save_job(db: db_dependency, user: user_dependency, job_id: int):
    profile = get_my_profile(db, user)

    job = db.get(Jobs, job_id)
    if not job or job.status not in PUBLIC_STATUSES:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "open":
        raise HTTPException(status_code=409, detail="Only open jobs can be saved")

    already = (
        db.query(SavedJobs)
        .filter(SavedJobs.candidate_id == profile.id, SavedJobs.job_id == job_id)
        .first()
    )
    if already:
        raise HTTPException(status_code=409, detail="You already saved this job")

    saved = SavedJobs(candidate_id=profile.id, job_id=job_id)
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return to_out(saved, job, db.get(Companies, job.company_id))


# ---------------------------------------------------------------------------
# Item 113: my saved jobs (newest first)
# ---------------------------------------------------------------------------

@router.get("", response_model=list[SavedJobOut])
def get_saved_jobs(
    db: db_dependency,
    user: user_dependency,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    profile = get_my_profile(db, user)

    rows = (
        db.query(SavedJobs, Jobs, Companies)
        .join(Jobs, Jobs.id == SavedJobs.job_id)
        .join(Companies, Companies.id == Jobs.company_id)
        .filter(SavedJobs.candidate_id == profile.id, Jobs.status.in_(PUBLIC_STATUSES))
        .order_by(SavedJobs.created_at.desc(), SavedJobs.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [to_out(saved, job, company) for saved, job, company in rows]


# ---------------------------------------------------------------------------
# Item 114: remove a saved job
# ---------------------------------------------------------------------------

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_saved_job(db: db_dependency, user: user_dependency, job_id: int):
    profile = get_my_profile(db, user)

    saved = (
        db.query(SavedJobs)
        .filter(SavedJobs.candidate_id == profile.id, SavedJobs.job_id == job_id)
        .first()
    )
    if not saved:
        raise HTTPException(status_code=404, detail="This job is not in your saved list")

    db.delete(saved)
    db.commit()
