# Backward compatibility: Re-export from src.database
from src.database import DATABASE_URL, SessionLocal, engine, get_db, normalize_database_url

__all__ = ["DATABASE_URL", "SessionLocal", "engine", "get_db", "normalize_database_url"]
