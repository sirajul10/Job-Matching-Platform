from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base,sessionmaker

DB_URL = "postgresql://postgres.jgvzbpmbdedknjifcqky:UAvruv5AfadnxOO6@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"

engine = create_engine(DB_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()
