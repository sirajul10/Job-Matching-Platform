
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError


from router.auth import db_dependency, user_dependency

import models

from Pydantic.applicationPydantic import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStatusUpdate,
    ApplicationStatusHistoryResponse,
    ApplicationTimelineEvent,
    ApplicationTimelineResponse,
    ApplicationActionRequest,
    ApplicationCommentCreate,
    ApplicationCommentResponse,
    ApplicationDocumentCreate,
    ApplicationDocumentResponse
)

router = APIRouter(
    prefix="/applications",
    tags=["Job Applications"]
)



@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def apply_for_job(
    application_data: ApplicationCreate,
    db: db_dependency,
    user: user_dependency
):
    # 1. Check candidate role
    if user.get("role") != "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can apply for jobs"
        )

    # 2. Find candidate profile
    candidate = db.query(models.CandidateProfile).filter(
        models.CandidateProfile.user_id == user.get("id")
    ).first()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found"
        )

    # 3. Check whether the job exists
    job = db.query(models.Jobs).filter(
        models.Jobs.id == application_data.job_id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # 4. Check whether the job is open
    if str(job.status) != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This job is not open for applications"
        )

    # 5. Prevent duplicate applications
    existing_application = db.query(models.Applications).filter(
        models.Applications.job_id == application_data.job_id,
        models.Applications.candidate_id == candidate.id
    ).first()

    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already applied for this job"
        )

    # 6. Create application
    new_application = models.Applications(
        job_id=application_data.job_id,
        candidate_id=candidate.id,
        resume_url=application_data.resume_url or candidate.resume_url,
        cover_letter=application_data.cover_letter,
        status="applied"
    )

    try:
        db.add(new_application)
        db.commit()
        db.refresh(new_application)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already applied for this job"
        )

    return new_application


@router.get("/my-applications", response_model=list[ApplicationResponse])
def get_my_applications(
    db: db_dependency,
    user: user_dependency
):
    if user.get("role") != "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can view their applications"
        )

    candidate = db.query(models.CandidateProfile).filter(
        models.CandidateProfile.user_id == user.get("id")
    ).first()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found"
        )

    applications = db.query(models.Applications).filter(
        models.Applications.candidate_id == candidate.id
    ).order_by(
        models.Applications.applied_at.desc()
    ).all()

    return applications


@router.get("/{job_id}/applicants", response_model=list[ApplicationResponse])
def get_job_applicants(
    job_id: int,
    db: db_dependency,
    user: user_dependency
):
    if user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can view job applicants"
        )

    company_member = db.query(models.CompanyMembers).filter(
        models.CompanyMembers.user_id == user.get("id")
    ).first()

    if not company_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of any company"
        )

    job = db.query(models.Jobs).filter(
        models.Jobs.id == job_id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    company_member = db.query(models.CompanyMembers).filter(
        models.CompanyMembers.user_id == user.get("id"),
        models.CompanyMembers.company_id == job.company_id
    ).first()

    if not company_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view applicants for this job"
        )

    applicants = db.query(models.Applications).filter(
        models.Applications.job_id == job_id
    ).order_by(
        models.Applications.applied_at.desc()
    ).all()

    return applicants


@router.patch("/{application_id}/withdraw", response_model=ApplicationResponse)
def withdraw_application(
    application_id: int,
    db: db_dependency,
    user: user_dependency
):
    # Only candidates can withdraw applications
    if user.get("role") != "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates can withdraw applications"
        )

    # Find the candidate profile
    candidate = db.query(models.CandidateProfile).filter(
        models.CandidateProfile.user_id == user.get("id")
    ).first()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found"
        )

    # Find the candidate's own application
    application = db.query(models.Applications).filter(
        models.Applications.id == application_id,
        models.Applications.candidate_id == candidate.id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # Only applications with applied status can be withdrawn
    if str(application.status) != "applied":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only applications with applied status can be withdrawn"
        )

    old_status = str(application.status)

    # Update application status
    setattr(application, "status", "withdrawn")

    # Record status history
    history = models.ApplicationStatusHistory(
        application_id=cast(int, application.id),
        changed_by=user.get("id"),
        old_status=old_status,
        new_status="withdrawn",
        note="Application withdrawn by candidate"
    )

    try:
        db.add(history)
        db.commit()
        db.refresh(application)

    except Exception:
        db.rollback()
        raise

    return application


@router.patch(
    "/{application_id}/status",
    response_model=ApplicationResponse
)
def update_application_status(
    application_id: int,
    status_data: ApplicationStatusUpdate,
    db: db_dependency,
    user: user_dependency
):
    # 1. Only employers can update application status
    if user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can update application status"
        )

    # 2. Find the application
    application = db.query(models.Applications).filter(
        models.Applications.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # 3. Find the job
    job = db.query(models.Jobs).filter(
        models.Jobs.id == application.job_id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # 4. Verify employer's company membership
    company_member = db.query(models.CompanyMembers).filter(
        models.CompanyMembers.user_id == user.get("id"),
        models.CompanyMembers.company_id == job.company_id
    ).first()

    if not company_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this application"
        )

    # 5. Prevent updates to withdrawn applications
    if str(application.status) == "withdrawn":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Withdrawn applications cannot be updated"
        )

    # 6. Validate status transition
    allowed_transitions = {
        "applied": ["reviewed", "rejected"],
        "reviewed": ["shortlisted", "rejected"],
        "shortlisted": ["interview", "rejected"],
        "interview": ["hired", "rejected"]
    }

    old_status = str(application.status)
    new_status = status_data.status

    if new_status not in allowed_transitions.get(old_status, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot change application status from {old_status} to {new_status}"
        )

    # 7. Update application status
    setattr(application, "status", new_status)

    # 8. Create status history
    history = models.ApplicationStatusHistory(
        application_id=cast(int, application.id),
        changed_by=user.get("id"),
        old_status=old_status,
        new_status=new_status,
        note=status_data.note
    )

    # 9. Save both changes in one transaction
    try:
        db.add(history)
        db.commit()
        db.refresh(application)

    except Exception:
        db.rollback()
        raise

    return application



@router.get(
    "/{application_id}/history",
    response_model=list[ApplicationStatusHistoryResponse]
)
def get_application_status_history(
    application_id: int,
    db: db_dependency,
    user: user_dependency
):
    # 1. Find the application
    application = db.query(models.Applications).filter(
        models.Applications.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # 2. Check candidate access
    if user.get("role") == "candidate":
        candidate = db.query(models.CandidateProfile).filter(
            models.CandidateProfile.user_id == user.get("id")
        ).first()

        if candidate is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this history"
            )

        if getattr(application, "candidate_id") != getattr(candidate, "id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this history"
            )

    # 3. Check employer access
    elif user.get("role") == "employer":
        job = db.query(models.Jobs).filter(
            models.Jobs.id == application.job_id
        ).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        company_member = db.query(models.CompanyMembers).filter(
            models.CompanyMembers.user_id == user.get("id"),
            models.CompanyMembers.company_id == job.company_id
        ).first()

        if not company_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this history"
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view application history"
        )

    # 4. Retrieve status history
    history = db.query(models.ApplicationStatusHistory).filter(
        models.ApplicationStatusHistory.application_id == application_id
    ).order_by(
        models.ApplicationStatusHistory.created_at.asc()
    ).all()

    return history


@router.get(
    "/{application_id}/timeline",
    response_model=ApplicationTimelineResponse
)
def get_application_timeline(
    application_id: int,
    db: db_dependency,
    user: user_dependency
):
    # 1. Find the application
    application = db.query(models.Applications).filter(
        models.Applications.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # 2. Check candidate access
    if user.get("role") == "candidate":
        candidate = db.query(models.CandidateProfile).filter(
            models.CandidateProfile.user_id == user.get("id")
        ).first()

        if candidate is None or getattr(application, "candidate_id") != getattr(candidate, "id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this timeline"
            )

    # 3. Check employer access
    elif user.get("role") == "employer":
        job = db.query(models.Jobs).filter(
            models.Jobs.id == application.job_id
        ).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        company_member = db.query(models.CompanyMembers).filter(
            models.CompanyMembers.user_id == user.get("id"),
            models.CompanyMembers.company_id == job.company_id
        ).first()

        if not company_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this timeline"
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this timeline"
        )

    # 4. Create the initial application event
    timeline = [
        ApplicationTimelineEvent(
            status="applied",
            changed_by=None,
            note="Application submitted",
            created_at=getattr(application, "applied_at")
        )
    ]

    # 5. Retrieve status history
    history_records = db.query(
        models.ApplicationStatusHistory
    ).filter(
        models.ApplicationStatusHistory.application_id == application_id
    ).order_by(
        models.ApplicationStatusHistory.created_at.asc()
    ).all()

    # 6. Add history records to timeline
    for record in history_records:
        timeline.append(
            ApplicationTimelineEvent(
                status=getattr(record, "new_status"),
                changed_by=getattr(record, "changed_by", None),
                note=getattr(record, "note", None),
                created_at=getattr(record, "created_at")
            )
        )

    # 7. Return complete timeline
    return ApplicationTimelineResponse(
        application_id=int(getattr(application, "id")),
        job_id=int(getattr(application, "job_id")),
        current_status=getattr(application, "status"),
        timeline=timeline
    )


@router.patch(
    "/{application_id}/shortlist",
    response_model=ApplicationResponse
)
def shortlist_candidate(
    application_id: int,
    action_data: ApplicationActionRequest,
    db: db_dependency,
    user: user_dependency
):
    # 1. Only employers can shortlist candidates
    if user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can shortlist candidates"
        )

    # 2. Find the application
    application = db.query(models.Applications).filter(
        models.Applications.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # 3. Find the associated job
    job = db.query(models.Jobs).filter(
        models.Jobs.id == application.job_id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # 4. Verify company membership
    company_member = db.query(models.CompanyMembers).filter(
        models.CompanyMembers.user_id == user.get("id"),
        models.CompanyMembers.company_id == job.company_id
    ).first()

    if not company_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to shortlist this candidate"
        )

    # 5. Validate status transition
    if str(application.status) != "reviewed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only reviewed applications can be shortlisted"
        )

    old_status = str(application.status)
    new_status = "shortlisted"

    # 6. Update application status
    setattr(application, "status", new_status)

    # 7. Create status history
    history = models.ApplicationStatusHistory(
        application_id=application.id,
        changed_by=user.get("id"),
        old_status=old_status,
        new_status=new_status,
        note=action_data.note
    )

    # 8. Commit both changes together
    try:
        db.add(history)
        db.commit()
        db.refresh(application)

    except Exception:
        db.rollback()
        raise

    return application



@router.patch(
    "/{application_id}/reject",
    response_model=ApplicationResponse
)
def reject_candidate(
    application_id: int,
    action_data: ApplicationActionRequest,
    db: db_dependency,
    user: user_dependency
):
    # 1. Only employers can reject candidates
    if user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can reject candidates"
        )

    # 2. Find the application
    application = db.query(models.Applications).filter(
        models.Applications.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # 3. Find the associated job
    job = db.query(models.Jobs).filter(
        models.Jobs.id == application.job_id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # 4. Verify company membership
    company_member = db.query(models.CompanyMembers).filter(
        models.CompanyMembers.user_id == user.get("id"),
        models.CompanyMembers.company_id == job.company_id
    ).first()

    if not company_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to reject this candidate"
        )

    # 5. Validate status transition
    allowed_statuses = [
        "applied",
        "reviewed",
        "shortlisted",
        "interview"
    ]

    old_status = str(application.status)

    if old_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This application cannot be rejected"
        )

    new_status = "rejected"

    # 6. Update application status
    setattr(application, "status", new_status)

    # 7. Create status history
    history = models.ApplicationStatusHistory(
        application_id=application.id,
        changed_by=user.get("id"),
        old_status=old_status,
        new_status=new_status,
        note=action_data.note
    )

    # 8. Commit both changes together
    try:
        db.add(history)
        db.commit()
        db.refresh(application)

    except Exception:
        db.rollback()
        raise

    return application



@router.post(
    "/{application_id}/comments",
    response_model=ApplicationCommentResponse,
    status_code=status.HTTP_201_CREATED
)
def add_application_comment(
    application_id: int,
    comment_data: ApplicationCommentCreate,
    db: db_dependency,
    user: user_dependency
):
    # 1. Only employers can add internal comments
    if user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can add internal comments"
        )

    # 2. Validate comment text
    comment_text = comment_data.comment.strip()

    if not comment_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment cannot be empty"
        )

    # 3. Find the application
    application = db.query(models.Applications).filter(
        models.Applications.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # 4. Find the associated job
    job = db.query(models.Jobs).filter(
        models.Jobs.id == application.job_id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # 5. Verify company membership
    company_member = db.query(models.CompanyMembers).filter(
        models.CompanyMembers.user_id == user.get("id"),
        models.CompanyMembers.company_id == job.company_id
    ).first()

    if not company_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to comment on this application"
        )

    # 6. Create the internal comment
    new_comment = models.ApplicationComments(
        application_id=application.id,
        user_id=user.get("id"),
        comment=comment_text
    )

    try:
        db.add(new_comment)
        db.commit()
        db.refresh(new_comment)

    except Exception:
        db.rollback()
        raise

    return new_comment



@router.get(
    "/{application_id}/comments",
    response_model=list[ApplicationCommentResponse]
)
def get_application_comments(
    application_id: int,
    db: db_dependency,
    user: user_dependency
):
    # 1. Only employers can view internal comments
    if user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can view internal comments"
        )

    # 2. Find the application
    application = db.query(models.Applications).filter(
        models.Applications.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # 3. Find the associated job
    job = db.query(models.Jobs).filter(
        models.Jobs.id == application.job_id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # 4. Verify company membership
    company_member = db.query(models.CompanyMembers).filter(
        models.CompanyMembers.user_id == user.get("id"),
        models.CompanyMembers.company_id == job.company_id
    ).first()

    if not company_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view these comments"
        )

    # 5. Retrieve comments in chronological order
    comments = db.query(models.ApplicationComments).filter(
        models.ApplicationComments.application_id == application_id
    ).order_by(
        models.ApplicationComments.created_at.asc()
    ).all()

    return comments



@router.post(
    "/{application_id}/documents",
    response_model=ApplicationDocumentResponse,
    status_code=status.HTTP_201_CREATED
)
def add_application_document(
    application_id: int,
    document_data: ApplicationDocumentCreate,
    db: db_dependency,
    user: user_dependency
):
    # 1. Only employers can add application documents
    if user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can add application documents"
        )

    # 2. Validate document information
    document_name = document_data.document_name.strip()
    document_url = document_data.document_url.strip()

    if not document_name or not document_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document name and URL cannot be empty"
        )

    # 3. Find the application
    application = db.query(models.Applications).filter(
        models.Applications.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # 4. Find the associated job
    job = db.query(models.Jobs).filter(
        models.Jobs.id == application.job_id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # 5. Verify company membership
    company_member = db.query(models.CompanyMembers).filter(
        models.CompanyMembers.user_id == user.get("id"),
        models.CompanyMembers.company_id == job.company_id
    ).first()

    if not company_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to add documents to this application"
        )

    # 6. Create the document record
    new_document = models.ApplicationDocuments(
        application_id=application.id,
        uploaded_by=user.get("id"),
        document_name=document_name,
        document_url=document_url,
        document_type=document_data.document_type
    )

    try:
        db.add(new_document)
        db.commit()
        db.refresh(new_document)

    except Exception:
        db.rollback()
        raise

    return new_document



@router.get(
    "/{application_id}/documents",
    response_model=list[ApplicationDocumentResponse]
)
def get_application_documents(
    application_id: int,
    db: db_dependency,
    user: user_dependency
):
    # 1. Only employers can view application documents
    if user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can view application documents"
        )

    # 2. Find the application
    application = db.query(models.Applications).filter(
        models.Applications.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # 3. Find the associated job
    job = db.query(models.Jobs).filter(
        models.Jobs.id == application.job_id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # 4. Verify company membership
    company_member = db.query(models.CompanyMembers).filter(
        models.CompanyMembers.user_id == user.get("id"),
        models.CompanyMembers.company_id == job.company_id
    ).first()

    if not company_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view these documents"
        )

    # 5. Retrieve documents in chronological order
    documents = db.query(models.ApplicationDocuments).filter(
        models.ApplicationDocuments.application_id == application_id
    ).order_by(
        models.ApplicationDocuments.uploaded_at.asc()
    ).all()

    return documents



@router.delete(
    "/{application_id}/documents/{document_id}"
)
def delete_application_document(
    application_id: int,
    document_id: int,
    db: db_dependency,
    user: user_dependency
):
    # 1. Only employers can delete application documents
    if user.get("role") != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can delete application documents"
        )

    # 2. Find the application
    application = db.query(models.Applications).filter(
        models.Applications.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # 3. Find the associated job
    job = db.query(models.Jobs).filter(
        models.Jobs.id == application.job_id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # 4. Verify company membership
    company_member = db.query(models.CompanyMembers).filter(
        models.CompanyMembers.user_id == user.get("id"),
        models.CompanyMembers.company_id == job.company_id
    ).first()

    if not company_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete these documents"
        )

    # 5. Find the document belonging to this application
    document = db.query(models.ApplicationDocuments).filter(
        models.ApplicationDocuments.id == document_id,
        models.ApplicationDocuments.application_id == application_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application document not found"
        )

    # 6. Delete the document record
    try:
        db.delete(document)
        db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "message": "Application document deleted successfully",
        "document_id": document_id
    }
