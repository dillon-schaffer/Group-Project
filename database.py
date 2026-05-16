import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()


def normalize_database_url(url: str) -> str:
    """Use the installed psycopg v3 driver for Render/local Postgres URLs."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


# Read from POSTGRES_URI (Supabase), then DATABASE_URL (Render), then local default
raw_url = (
    os.getenv("POSTGRES_URI")
    or os.getenv("DATABASE_URL")
    or "postgresql+psycopg://localhost/group_project"
)
DATABASE_URL = normalize_database_url(raw_url)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
