from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from router.auth import get_db, get_current_user
from router.skill import get_or_create_skill
from models import Jobs, JobSkills, Skills, Companies, CompanyMembers, Users, Applications, SavedJobs
from Pydantic.jobPydantic import JobCreate, JobUpdate, JobOut, JobActionResult

router = APIRouter(prefix="/jobs", tags=["Jobs"])

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

# fields copied from the request into the Jobs table (and copied again when duplicating)
JOB_FIELDS = [
    "title", "description", "requirements", "responsibilities",
    "location", "is_remote", "job_type", "experience_level",
    "salary_min", "salary_max", "currency", "expires_at",
]
HIDDEN_STATUSES = {"draft", "archived"}  # only the company's own people can see these


# ---------------------------------------------------------------------------
# Helpers (job_skills.py imports require_company_access too)
# ---------------------------------------------------------------------------

def find_company_access(db: Session, user: dict, company: Companies):
    """Returns (allowed, member). member is the CompanyMembers row, or None when
    the user is allowed only because they created the company or are a platform admin."""
    user_id = user.get("id")

    member = (
        db.query(CompanyMembers)
        .filter(CompanyMembers.user_id == user_id, CompanyMembers.company_id == company.id)
        .first()
    )
    if member:
        return True, member
    if company.created_by == user_id:
        return True, None

    account = db.get(Users, user_id)
    if account and account.role == "admin":
        return True, None
    return False, None


def require_company_access(db: Session, user: dict, company_id: int):
    company = db.get(Companies, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    allowed, member = find_company_access(db, user, company)
    if not allowed:
        raise HTTPException(status_code=403, detail="You do not have access to this company")
    return member


def get_job_or_404(db: Session, job_id: int) -> Jobs:
    job = db.get(Jobs, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def ensure_not_expired(job: Jobs):
    if job.expires_at is None:
        return
    expires = job.expires_at if job.expires_at.tzinfo else job.expires_at.replace(tzinfo=timezone.utc)
    if expires <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="This job's expiry date has passed. Update expires_at first.")


def to_out(db: Session, job: Jobs) -> dict:
    company = db.get(Companies, job.company_id)
    skill_rows = (
        db.query(JobSkills, Skills)
        .join(Skills, Skills.id == JobSkills.skill_id)
        .filter(JobSkills.job_id == job.id)
        .order_by(JobSkills.is_required.desc(), Skills.name)
        .all()
    )

    data = {field: getattr(job, field) for field in JOB_FIELDS}
    data.update(
        id=job.id,
        company_id=job.company_id,
        company_name=company.name,
        posted_by=job.posted_by,
        status=job.status,
        posted_at=job.posted_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
        skills=[{"skill_id": s.id, "name": s.name, "is_required": js.is_required} for js, s in skill_rows],
    )
    return data


# ---------------------------------------------------------------------------
# Item 60: create (and publish) a job
# ---------------------------------------------------------------------------

@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(db: db_dependency, user: user_dependency, payload: JobCreate):
    member = require_company_access(db, user, payload.company_id)

    # skills first: unknown skills are created automatically (item 35)
    skill_flags: dict[int, bool] = {}
    for item in payload.skills:
        skill = get_or_create_skill(db, item.name)
        skill_flags.setdefault(skill.id, item.is_required)

    job = Jobs(
        company_id=payload.company_id,
        posted_by=member.id if member else None,  # posted_by points to company_members, not users
        status=payload.status,
        **payload.model_dump(include=set(JOB_FIELDS)),
    )
    db.add(job)
    db.flush()  # gives the job an id

    for skill_id, is_required in skill_flags.items():
        db.add(JobSkills(job_id=job.id, skill_id=skill_id, is_required=is_required))

    db.commit()
    db.refresh(job)
    return to_out(db, job)


# ---------------------------------------------------------------------------
# Item 61: job details
# ---------------------------------------------------------------------------

@router.get("/{job_id}", response_model=JobOut)
def get_job(db: db_dependency, user: user_dependency, job_id: int):
    job = get_job_or_404(db, job_id)

    if job.status in HIDDEN_STATUSES:
        allowed, _ = find_company_access(db, user, db.get(Companies, job.company_id))
        if not allowed:
            raise HTTPException(status_code=404, detail="Job not found")  # don't reveal that it exists

    return to_out(db, job)


# ---------------------------------------------------------------------------
# Item 62: update a job
# ---------------------------------------------------------------------------

@router.put("/{job_id}", response_model=JobOut)
def update_job(db: db_dependency, user: user_dependency, job_id: int, payload: JobUpdate):
    job = get_job_or_404(db, job_id)
    require_company_access(db, user, job.company_id)

    if job.status == "archived":
        raise HTTPException(status_code=409, detail="Archived jobs cannot be edited")

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")

    for key, value in changes.items():
        setattr(job, key, value)

    # re-check the salary against the values that are stored now
    if job.salary_min is not None and job.salary_max is not None and job.salary_min > job.salary_max:
        raise HTTPException(status_code=400, detail="salary_min cannot be greater than salary_max")
    if (job.salary_min is not None or job.salary_max is not None) and not job.currency:
        raise HTTPException(status_code=400, detail="currency is required when a salary is given")

    db.commit()
    db.refresh(job)
    return to_out(db, job)


# ---------------------------------------------------------------------------
# Items 60, 64, 65: status changes (draft -> open -> closed -> open)
# ---------------------------------------------------------------------------

@router.post("/{job_id}/publish", response_model=JobOut)
def publish_job(db: db_dependency, user: user_dependency, job_id: int):
    job = get_job_or_404(db, job_id)
    require_company_access(db, user, job.company_id)

    if job.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft jobs can be published")
    ensure_not_expired(job)

    job.status = "open"
    db.commit()
    db.refresh(job)
    return to_out(db, job)


@router.post("/{job_id}/close", response_model=JobOut)
def close_job(db: db_dependency, user: user_dependency, job_id: int):
    job = get_job_or_404(db, job_id)
    require_company_access(db, user, job.company_id)

    if job.status != "open":
        raise HTTPException(status_code=409, detail="Only open jobs can be closed")

    job.status = "closed"
    db.commit()
    db.refresh(job)
    return to_out(db, job)


@router.post("/{job_id}/reopen", response_model=JobOut)
def reopen_job(db: db_dependency, user: user_dependency, job_id: int):
    job = get_job_or_404(db, job_id)
    require_company_access(db, user, job.company_id)

    if job.status != "closed":
        raise HTTPException(status_code=409, detail="Only closed jobs can be reopened")
    ensure_not_expired(job)

    job.status = "open"
    db.commit()
    db.refresh(job)
    return to_out(db, job)


# ---------------------------------------------------------------------------
# Item 63: delete or archive
# ---------------------------------------------------------------------------

@router.delete("/{job_id}", response_model=JobActionResult)
def delete_job(db: db_dependency, user: user_dependency, job_id: int):
    job = get_job_or_404(db, job_id)
    require_company_access(db, user, job.company_id)

    has_applications = db.query(Applications).filter(Applications.job_id == job_id).first() is not None

    if has_applications:
        # deleting would wipe the candidates' applications too, so archive instead
        if job.status == "archived":
            raise HTTPException(status_code=409, detail="Job is already archived")
        job.status = "archived"
        db.commit()
        return {"message": "This job has applications, so it was archived instead of deleted", "action": "archived"}

    db.query(JobSkills).filter(JobSkills.job_id == job_id).delete()
    db.query(SavedJobs).filter(SavedJobs.job_id == job_id).delete()
    db.delete(job)
    db.commit()
    return {"message": "Job deleted", "action": "deleted"}


# ---------------------------------------------------------------------------
# Item 66: duplicate a job
# ---------------------------------------------------------------------------

@router.post("/{job_id}/duplicate", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def duplicate_job(db: db_dependency, user: user_dependency, job_id: int):
    original = get_job_or_404(db, job_id)
    member = require_company_access(db, user, original.company_id)

    # the copy starts as a draft with no expiry date; everything else is copied
    data = {field: getattr(original, field) for field in JOB_FIELDS if field != "expires_at"}
    copy = Jobs(
        company_id=original.company_id,
        posted_by=member.id if member else None,
        status="draft",
        **data,
    )
    db.add(copy)
    db.flush()

    for row in db.query(JobSkills).filter(JobSkills.job_id == original.id).all():
        db.add(JobSkills(job_id=copy.id, skill_id=row.skill_id, is_required=row.is_required))

    db.commit()
    db.refresh(copy)
    return to_out(db, copy)
