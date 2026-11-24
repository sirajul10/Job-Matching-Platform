import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base,sessionmaker
from dotenv import load_dotenv

load_dotenv()

# DB_URL = "postgresql://postgres.jgvzbpmbdedknjifcqky:UAvruv5AfadnxOO6@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
DB_URL = os.getenv("DB_URL")

if not DB_URL:
    raise ValueError("DB_URL is not configured")


engine = create_engine(DB_URL)



SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()
