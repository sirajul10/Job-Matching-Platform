from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from router.auth import get_db, get_current_user
from router.candidate_skills import get_my_profile
from router.skill import get_or_create_skill
from models import JobAlerts, JobAlertSkills, Jobs, JobSkills, Skills, CandidateProfile
from Pydantic.jobAlertPydantic import JobAlertCreate, JobAlertUpdate, JobAlertOut

router = APIRouter(prefix="/job-alerts", tags=["Job Alerts"])

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

MAX_ALERTS_PER_CANDIDATE = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_my_alert(db: Session, profile: CandidateProfile, alert_id: int) -> JobAlerts:
    alert = (
        db.query(JobAlerts)
        .filter(JobAlerts.id == alert_id, JobAlerts.candidate_id == profile.id)
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Job alert not found")  # also used for other people's alerts
    return alert


def resolve_skill_ids(db: Session, names: list[str]) -> list[int]:
    """Skill names -> skill ids (unknown names are created, like everywhere else). Call this first:
    get_or_create_skill can roll back the session in a rare race."""
    ids: list[int] = []
    for name in names:
        skill_id = get_or_create_skill(db, name).id
        if skill_id not in ids:
            ids.append(skill_id)
    return ids


def to_out(db: Session, alert: JobAlerts) -> dict:
    skill_names = [
        name for (name,) in
        db.query(Skills.name)
        .join(JobAlertSkills, JobAlertSkills.skill_id == Skills.id)
        .filter(JobAlertSkills.alert_id == alert.id)
        .order_by(Skills.name)
    ]
    return {
        "id": alert.id,
        "name": alert.name,
        "keyword": alert.keyword,
        "location": alert.location,
        "is_remote": alert.is_remote,
        "job_type": alert.job_type,
        "experience_level": alert.experience_level,
        "min_salary": alert.min_salary,
        "currency": alert.currency,
        "skills": skill_names,
        "is_active": alert.is_active,
        "created_at": alert.created_at,
        "updated_at": alert.updated_at,
    }


def has_any_filter(alert: JobAlerts, has_skills: bool) -> bool:
    return any([
        alert.keyword, alert.location, alert.is_remote is not None, alert.job_type,
        alert.experience_level, alert.min_salary is not None, has_skills,
    ])


# ---------------------------------------------------------------------------
# Item 115: create an alert
# ---------------------------------------------------------------------------

@router.post("", response_model=JobAlertOut, status_code=status.HTTP_201_CREATED)
def create_alert(db: db_dependency, user: user_dependency, payload: JobAlertCreate):
    profile = get_my_profile(db, user)

    count = db.query(JobAlerts).filter(JobAlerts.candidate_id == profile.id).count()
    if count >= MAX_ALERTS_PER_CANDIDATE:
        raise HTTPException(status_code=409, detail=f"You can have at most {MAX_ALERTS_PER_CANDIDATE} job alerts")

    skill_ids = resolve_skill_ids(db, payload.skills)

    alert = JobAlerts(candidate_id=profile.id, **payload.model_dump(exclude={"skills"}))
    db.add(alert)
    db.flush()  # gives the alert an id

    for skill_id in skill_ids:
        db.add(JobAlertSkills(alert_id=alert.id, skill_id=skill_id))

    db.commit()
    db.refresh(alert)
    return to_out(db, alert)


# ---------------------------------------------------------------------------
# Item 118: my alerts
# ---------------------------------------------------------------------------

@router.get("", response_model=list[JobAlertOut])
def get_my_alerts(db: db_dependency, user: user_dependency):
    profile = get_my_profile(db, user)

    alerts = (
        db.query(JobAlerts)
        .filter(JobAlerts.candidate_id == profile.id)
        .order_by(JobAlerts.created_at.desc(), JobAlerts.id.desc())
        .all()
    )
    return [to_out(db, alert) for alert in alerts]


# ---------------------------------------------------------------------------
# Item 116: update an alert
# ---------------------------------------------------------------------------

@router.put("/{alert_id}", response_model=JobAlertOut)
def update_alert(db: db_dependency, user: user_dependency, alert_id: int, payload: JobAlertUpdate):
    profile = get_my_profile(db, user)
    alert = get_my_alert(db, profile, alert_id)

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")

    new_skill_ids = None
    if "skills" in changes:
        new_skill_ids = resolve_skill_ids(db, changes.pop("skills") or [])

    for key, value in changes.items():
        setattr(alert, key, value)

    if new_skill_ids is not None:
        has_skills = bool(new_skill_ids)
    else:
        has_skills = db.query(JobAlertSkills).filter(JobAlertSkills.alert_id == alert.id).first() is not None

    if not has_any_filter(alert, has_skills):
        raise HTTPException(status_code=400, detail="An alert needs at least one search preference")
    if alert.min_salary is not None and not alert.currency:
        raise HTTPException(status_code=400, detail="currency is required when min_salary is given")

    if new_skill_ids is not None:
        db.query(JobAlertSkills).filter(JobAlertSkills.alert_id == alert.id).delete()
        for skill_id in new_skill_ids:
            db.add(JobAlertSkills(alert_id=alert.id, skill_id=skill_id))

    db.commit()
    db.refresh(alert)
    return to_out(db, alert)


# ---------------------------------------------------------------------------
# Item 117: delete an alert
# ---------------------------------------------------------------------------

@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(db: db_dependency, user: user_dependency, alert_id: int):
    profile = get_my_profile(db, user)
    alert = get_my_alert(db, profile, alert_id)

    db.query(JobAlertSkills).filter(JobAlertSkills.alert_id == alert.id).delete()
    db.delete(alert)
    db.commit()


# ---------------------------------------------------------------------------
# Item 119: which alerts match a job? (the Notifications module calls this when a job is published)
# ---------------------------------------------------------------------------

def alert_matches_job(alert: JobAlerts, alert_skill_ids: set[int], job: Jobs, job_skill_ids: set[int]) -> bool:
    """Every preference the alert has must match. Skills match if the job needs at least one of them."""
    if alert.keyword and alert.keyword.lower() not in f"{job.title} {job.description}".lower():
        return False
    if alert.location and (not job.location or alert.location.lower() not in job.location.lower()):
        return False
    if alert.is_remote is not None and job.is_remote != alert.is_remote:
        return False
    if alert.job_type and job.job_type != alert.job_type:
        return False
    if alert.experience_level and job.experience_level != alert.experience_level:
        return False
    if alert.min_salary is not None:
        best_pay = job.salary_max if job.salary_max is not None else job.salary_min
        if best_pay is None or job.currency != alert.currency or best_pay < alert.min_salary:
            return False
    if alert_skill_ids and not (alert_skill_ids & job_skill_ids):
        return False
    return True


def find_matching_alerts(db: Session, job: Jobs) -> list[JobAlerts]:
    """Active alerts that match this job. Only open jobs match anything."""
    if job.status != "open":
        return []

    alerts = db.query(JobAlerts).filter(JobAlerts.is_active.is_(True)).all()
    if not alerts:
        return []

    skills_by_alert: dict[int, set[int]] = defaultdict(set)
    rows = db.query(JobAlertSkills.alert_id, JobAlertSkills.skill_id).filter(
        JobAlertSkills.alert_id.in_([alert.id for alert in alerts])
    )
    for alert_id, skill_id in rows:
        skills_by_alert[alert_id].add(skill_id)

    job_skill_ids = {skill_id for (skill_id,) in db.query(JobSkills.skill_id).filter(JobSkills.job_id == job.id)}

    return [alert for alert in alerts if alert_matches_job(alert, skills_by_alert[alert.id], job, job_skill_ids)]
