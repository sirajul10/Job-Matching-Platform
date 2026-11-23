import re
from collections import Counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from router.auth import get_db, get_current_user
from models import (
    Skills, CandidateSkills, JobSkills,
    SkillCategories, SkillCategoryLinks, Users,
)
from Pydantic.skillPydantic import (
    SkillCreate, SkillUpdate, SkillOut,
    CategoryCreate, CategoryOut,
    PopularSkillOut, RelatedSkillOut,
    DuplicateGroup, MergeRequest, MergeResult,
)

router = APIRouter(prefix="/skills", tags=["Skills"])

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# Helpers (the other skill routers import these too)
# ---------------------------------------------------------------------------

def require_admin(db: Session, user: dict):
    account = db.get(Users, user.get("id"))
    if not account or account.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


def find_by_name(db: Session, name: str, exclude_id: int | None = None):
    """Case-insensitive lookup, so 'Python' and 'python' are the same skill."""
    query = db.query(Skills).filter(func.lower(Skills.name) == name.lower())
    if exclude_id is not None:
        query = query.filter(Skills.id != exclude_id)
    return query.first()


def get_or_create_skill(db: Session, name: str) -> Skills:
    """Item 35: return the skill if it exists, otherwise create it."""
    name = " ".join(name.split())
    skill = find_by_name(db, name)
    if skill:
        return skill

    skill = Skills(name=name)
    db.add(skill)
    try:
        db.flush()  # sends the INSERT now, so skill.id is available
    except IntegrityError:
        # someone else created the same skill a moment ago
        db.rollback()
        skill = find_by_name(db, name)
        if not skill:
            raise
    return skill


def duplicate_key(name: str) -> str:
    """'Node.js', 'NodeJS' and 'node js' all become 'nodejs'. Keeps + and # so C++ and C# stay different."""
    return re.sub(r"[^a-z0-9+#]", "", name.lower())


def find_category_by_name(db: Session, name: str, exclude_id: int | None = None):
    query = db.query(SkillCategories).filter(func.lower(SkillCategories.name) == name.lower())
    if exclude_id is not None:
        query = query.filter(SkillCategories.id != exclude_id)
    return query.first()


# ---------------------------------------------------------------------------
# Items 29-33: master skills (fixed paths like /popular must stay above /{skill_id})
# ---------------------------------------------------------------------------

@router.post("", response_model=SkillOut, status_code=status.HTTP_201_CREATED)
def create_skill(db: db_dependency, user: user_dependency, payload: SkillCreate):
    require_admin(db, user)

    if find_by_name(db, payload.name):
        raise HTTPException(status_code=409, detail="Skill already exists")

    skill = Skills(name=payload.name)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.get("", response_model=list[SkillOut])
def list_skills(
    db: db_dependency,
    user: user_dependency,
    search: str | None = None,
    category_id: int | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    query = db.query(Skills)
    if search:
        query = query.filter(Skills.name.ilike(f"%{search.strip()}%"))
    if category_id is not None:
        query = query.join(SkillCategoryLinks, SkillCategoryLinks.skill_id == Skills.id).filter(
            SkillCategoryLinks.category_id == category_id
        )
    return query.order_by(Skills.name).offset(skip).limit(limit).all()


# ---------------------------------------------------------------------------
# Item 38: popular skills
# ---------------------------------------------------------------------------

@router.get("/popular", response_model=list[PopularSkillOut])
def popular_skills(db: db_dependency, user: user_dependency, limit: int = Query(10, ge=1, le=50)):
    cand_sub = (
        db.query(CandidateSkills.skill_id.label("skill_id"), func.count(CandidateSkills.id).label("n"))
        .group_by(CandidateSkills.skill_id)
        .subquery()
    )
    job_sub = (
        db.query(JobSkills.skill_id.label("skill_id"), func.count(JobSkills.id).label("n"))
        .group_by(JobSkills.skill_id)
        .subquery()
    )
    cand_n = func.coalesce(cand_sub.c.n, 0)
    job_n = func.coalesce(job_sub.c.n, 0)
    total = cand_n + job_n

    rows = (
        db.query(Skills.id, Skills.name, cand_n.label("candidates"), job_n.label("jobs"), total.label("total"))
        .outerjoin(cand_sub, cand_sub.c.skill_id == Skills.id)
        .outerjoin(job_sub, job_sub.c.skill_id == Skills.id)
        .filter(total > 0)
        .order_by(total.desc(), Skills.name)
        .limit(limit)
        .all()
    )
    return [
        {"id": r.id, "name": r.name, "candidates": r.candidates, "jobs": r.jobs, "total": r.total}
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Item 40: duplicate skills (detect + merge)
# ---------------------------------------------------------------------------

@router.get("/duplicates", response_model=list[DuplicateGroup])
def find_duplicates(db: db_dependency, user: user_dependency):
    require_admin(db, user)

    groups: dict[str, list[Skills]] = {}
    for skill in db.query(Skills).order_by(Skills.name).all():
        key = duplicate_key(skill.name)
        if key:
            groups.setdefault(key, []).append(skill)

    return [{"skills": members} for members in groups.values() if len(members) > 1]


@router.post("/merge", response_model=MergeResult)
def merge_skills(db: db_dependency, user: user_dependency, payload: MergeRequest):
    require_admin(db, user)

    dup_ids = set(payload.duplicate_ids)
    if payload.target_id in dup_ids:
        raise HTTPException(status_code=400, detail="The target skill cannot also be a duplicate")

    target = db.get(Skills, payload.target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target skill not found")

    duplicates = db.query(Skills).filter(Skills.id.in_(dup_ids)).all()
    if len(duplicates) != len(dup_ids):
        raise HTTPException(status_code=404, detail="One or more duplicate skills were not found")

    for dup in duplicates:
        # candidates who have the duplicate skill
        for row in db.query(CandidateSkills).filter(CandidateSkills.skill_id == dup.id).all():
            existing = (
                db.query(CandidateSkills)
                .filter(CandidateSkills.candidate_id == row.candidate_id, CandidateSkills.skill_id == target.id)
                .first()
            )
            if existing:  # already has the target: keep the higher experience, drop the extra row
                existing.years_of_experience = max(existing.years_of_experience, row.years_of_experience)
                db.delete(row)
            else:
                row.skill_id = target.id

        # jobs that require the duplicate skill
        for row in db.query(JobSkills).filter(JobSkills.skill_id == dup.id).all():
            existing = (
                db.query(JobSkills)
                .filter(JobSkills.job_id == row.job_id, JobSkills.skill_id == target.id)
                .first()
            )
            if existing:  # keep "required" if either row was required
                existing.is_required = existing.is_required or row.is_required
                db.delete(row)
            else:
                row.skill_id = target.id

        # categories of the duplicate skill
        for row in db.query(SkillCategoryLinks).filter(SkillCategoryLinks.skill_id == dup.id).all():
            existing = (
                db.query(SkillCategoryLinks)
                .filter(SkillCategoryLinks.skill_id == target.id, SkillCategoryLinks.category_id == row.category_id)
                .first()
            )
            if existing:
                db.delete(row)
            else:
                row.skill_id = target.id

        db.flush()  # apply the moves first (autoflush is off in this project)
        db.delete(dup)
        db.flush()

    db.commit()
    db.refresh(target)
    return {"merged_count": len(duplicates), "target": target}


# ---------------------------------------------------------------------------
# Item 34: skill categories
# ---------------------------------------------------------------------------

@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(db: db_dependency, user: user_dependency, payload: CategoryCreate):
    require_admin(db, user)

    if find_category_by_name(db, payload.name):
        raise HTTPException(status_code=409, detail="Category already exists")

    category = SkillCategories(name=payload.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return {"id": category.id, "name": category.name, "skill_count": 0}


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: db_dependency, user: user_dependency):
    rows = (
        db.query(SkillCategories, func.count(SkillCategoryLinks.id))
        .outerjoin(SkillCategoryLinks, SkillCategoryLinks.category_id == SkillCategories.id)
        .group_by(SkillCategories.id)
        .order_by(SkillCategories.name)
        .all()
    )
    return [{"id": c.id, "name": c.name, "skill_count": n} for c, n in rows]


@router.put("/categories/{category_id}", response_model=CategoryOut)
def update_category(db: db_dependency, user: user_dependency, category_id: int, payload: CategoryCreate):
    require_admin(db, user)

    category = db.get(SkillCategories, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if find_category_by_name(db, payload.name, exclude_id=category_id):
        raise HTTPException(status_code=409, detail="Category already exists")

    category.name = payload.name
    db.commit()
    count = db.query(SkillCategoryLinks).filter(SkillCategoryLinks.category_id == category_id).count()
    return {"id": category.id, "name": category.name, "skill_count": count}


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(db: db_dependency, user: user_dependency, category_id: int):
    require_admin(db, user)

    category = db.get(SkillCategories, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # only the links are removed, the skills themselves stay
    db.query(SkillCategoryLinks).filter(SkillCategoryLinks.category_id == category_id).delete()
    db.delete(category)
    db.commit()


# ---------------------------------------------------------------------------
# Items 29-33 again: one skill by id
# ---------------------------------------------------------------------------

@router.get("/{skill_id}", response_model=SkillOut)
def get_skill(db: db_dependency, user: user_dependency, skill_id: int):
    skill = db.get(Skills, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.put("/{skill_id}", response_model=SkillOut)
def update_skill(db: db_dependency, user: user_dependency, skill_id: int, payload: SkillUpdate):
    require_admin(db, user)

    skill = db.get(Skills, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    if find_by_name(db, payload.name, exclude_id=skill_id):
        raise HTTPException(status_code=409, detail="Skill already exists")

    skill.name = payload.name
    db.commit()
    db.refresh(skill)
    return skill


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(db: db_dependency, user: user_dependency, skill_id: int):
    require_admin(db, user)

    skill = db.get(Skills, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    in_use = (
        db.query(CandidateSkills).filter(CandidateSkills.skill_id == skill_id).first()
        or db.query(JobSkills).filter(JobSkills.skill_id == skill_id).first()
    )
    if in_use:
        raise HTTPException(status_code=409, detail="Skill is used by candidates or jobs and cannot be deleted")

    db.query(SkillCategoryLinks).filter(SkillCategoryLinks.skill_id == skill_id).delete()
    db.delete(skill)
    db.commit()


# ---------------------------------------------------------------------------
# Item 39: related skills
# ---------------------------------------------------------------------------

@router.get("/{skill_id}/related", response_model=list[RelatedSkillOut])
def related_skills(db: db_dependency, user: user_dependency, skill_id: int, limit: int = Query(10, ge=1, le=50)):
    if not db.get(Skills, skill_id):
        raise HTTPException(status_code=404, detail="Skill not found")

    scores: Counter = Counter()

    # +1 for every candidate who has both skills
    other_cand = aliased(CandidateSkills)
    rows = (
        db.query(other_cand.skill_id, func.count(other_cand.id))
        .join(CandidateSkills, CandidateSkills.candidate_id == other_cand.candidate_id)
        .filter(CandidateSkills.skill_id == skill_id, other_cand.skill_id != skill_id)
        .group_by(other_cand.skill_id)
        .all()
    )
    for sid, n in rows:
        scores[sid] += n

    # +1 for every job that asks for both skills
    other_job = aliased(JobSkills)
    rows = (
        db.query(other_job.skill_id, func.count(other_job.id))
        .join(JobSkills, JobSkills.job_id == other_job.job_id)
        .filter(JobSkills.skill_id == skill_id, other_job.skill_id != skill_id)
        .group_by(other_job.skill_id)
        .all()
    )
    for sid, n in rows:
        scores[sid] += n

    # +1 for every skill in the same category
    category_ids = [c for (c,) in db.query(SkillCategoryLinks.category_id).filter(SkillCategoryLinks.skill_id == skill_id)]
    if category_ids:
        rows = (
            db.query(SkillCategoryLinks.skill_id)
            .filter(SkillCategoryLinks.category_id.in_(category_ids), SkillCategoryLinks.skill_id != skill_id)
            .distinct()
            .all()
        )
        for (sid,) in rows:
            scores[sid] += 1

    top = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]
    if not top:
        return []

    names = {s.id: s.name for s in db.query(Skills).filter(Skills.id.in_([sid for sid, _ in top])).all()}
    return [{"id": sid, "name": names[sid], "score": score} for sid, score in top]


# ---------------------------------------------------------------------------
# Item 34 again: put a skill in / take it out of a category
# ---------------------------------------------------------------------------

@router.post("/{skill_id}/categories/{category_id}", status_code=status.HTTP_201_CREATED)
def add_skill_to_category(db: db_dependency, user: user_dependency, skill_id: int, category_id: int):
    require_admin(db, user)

    if not db.get(Skills, skill_id):
        raise HTTPException(status_code=404, detail="Skill not found")
    if not db.get(SkillCategories, category_id):
        raise HTTPException(status_code=404, detail="Category not found")

    link = (
        db.query(SkillCategoryLinks)
        .filter(SkillCategoryLinks.skill_id == skill_id, SkillCategoryLinks.category_id == category_id)
        .first()
    )
    if link:
        raise HTTPException(status_code=409, detail="Skill is already in this category")

    db.add(SkillCategoryLinks(skill_id=skill_id, category_id=category_id))
    db.commit()
    return {"message": "Skill added to category"}


@router.delete("/{skill_id}/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_skill_from_category(db: db_dependency, user: user_dependency, skill_id: int, category_id: int):
    require_admin(db, user)

    link = (
        db.query(SkillCategoryLinks)
        .filter(SkillCategoryLinks.skill_id == skill_id, SkillCategoryLinks.category_id == category_id)
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Skill is not in this category")

    db.delete(link)
    db.commit()
