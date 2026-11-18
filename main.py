from database import Base, SessionLocal, engine
import models
from fastapi import FastAPI, Depends, HTTPException
from router import auth,candidate

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(auth.router)
app.include_router(candidate.router)