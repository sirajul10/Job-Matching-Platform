from database import Base, SessionLocal, engine
import models
from fastapi import FastAPI, Depends, HTTPException
from router import auth, candidate, company, experience, skill, candidate_skills, job_skills


models.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(auth.router)
app.include_router(candidate.router)
app.include_router(company.router)
app.include_router(experience.router)
app.include_router(skill.router)
app.include_router(candidate_skills.router)
app.include_router(job_skills.router)

