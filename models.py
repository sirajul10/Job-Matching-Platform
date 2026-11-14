
from database import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, Date, Text,UniqueConstraint,Float
from sqlalchemy.sql import func


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="candidate", nullable=False)  # candidate / employer / admin
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=True)
    location = Column(String(150), nullable=True)
    headline = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    resume_url = Column(String(500), nullable=True)
    expected_salary = Column(Numeric(12, 2), nullable=True)
    open_to_work = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)


class Education(Base):
    __tablename__ = "education"

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    institution = Column(String(200), nullable=False)
    degree = Column(String(100), nullable=False)
    field_of_study = Column(String(150), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    still_running = Column(Boolean, default=False, nullable=False)
    grade = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)


class Experience(Base):
    __tablename__ = "experience"

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)

    company_name = Column(String(200), nullable=False)
    title = Column(String(150), nullable=False)
    employment_type = Column(String(50), nullable=True)  # Full-time / Part-time / Internship / Contract
    location = Column(String(150), nullable=True)
    description = Column(Text, nullable=True)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    still_running = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

# company site 


class Companies(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)
    logo_url = Column(String(500), nullable=True)
    industry = Column(String(150), nullable=True)
    size = Column(Integer, nullable=True)  # Number of employees
    location = Column(String(200), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)


class CompanyMembers(Base):
    __tablename__ = "company_members"

    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_user_company"),
    ) # to prevent same user and same company duplicate value

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), default="recruiter", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Jobs(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    posted_by = Column(Integer, ForeignKey("company_members.id", ondelete="SET NULL"), nullable=True)

    # Job information
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)

    # Job location and type
    location = Column(String(200), nullable=True)
    is_remote = Column(Boolean, default=False, nullable=False)
    job_type = Column(String(30), nullable=False)  # full-time / part-time / contract / internship
    experience_level = Column(String(30), nullable=True)  # entry / junior / mid / senior

    # Salary information
    salary_min = Column(Numeric(12, 2), nullable=True)
    salary_max = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), nullable=True)  # MYR / USD / SGD

    # Job status
    status = Column(String(20), default="draft", nullable=False)  # draft / open / closed

    # Dates
    posted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)



class Skills(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)


class CandidateSkills(Base):
    __tablename__ = "candidate_skills"

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    years_of_experience = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("candidate_id", "skill_id", name="uq_candidate_skill"),
    )


class JobSkills(Base):
    __tablename__ = "job_skills"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    is_required = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("job_id", "skill_id", name="uq_job_skill"),
    )


class Applications(Base):
    __tablename__ = 'applications'
    id = Column(Integer, primary_key=True) 
    job_id = Column(Integer, ForeignKey('jobs.id'))
    candidate_id = Column(Integer, ForeignKey('candidate_profiles.id'))
    resume_url = Column(String)
    cover_letter = Column(Text)
    status = Column(String) #applied / reviewed / shortlisted / interview / rejected / hired
    applied_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        UniqueConstraint("job_id",'candidate_id', name="uq_job_candidate")
    )
