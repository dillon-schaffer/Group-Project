import os
import logging
from functools import lru_cache

from dotenv import find_dotenv, load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load default.env first (won't override existing env vars)
load_dotenv(dotenv_path="default.env", override=False)

# Then load .env if it exists (will override default.env values)
load_dotenv(dotenv_path=find_dotenv(".env"), override=True)


class Settings:
    API_KEY: str | None = os.getenv("API_KEY")
    POSTGRES_URI: str | None = os.getenv("POSTGRES_URI")
    POSTGRES_URL: str | None = os.getenv("POSTGRES_URL")
    DATABASE_URL: str | None = os.getenv("DATABASE_URL")

    def __init__(self):
        # Check multiple env var names for database URL (priority order)
        self.database_url = (
            self.POSTGRES_URI      # Supabase default
            or self.POSTGRES_URL   # Render convention
            or self.DATABASE_URL   # Generic fallback
            or "postgresql+psycopg://localhost/group_project"  # Local default
        )
        
        # Debug logging for deployment troubleshooting (using logger instead of print)
        logger.debug(f"API_KEY set: {bool(self.API_KEY)}")
        logger.debug(f"POSTGRES_URI set: {bool(self.POSTGRES_URI)}")
        logger.debug(f"POSTGRES_URL set: {bool(self.POSTGRES_URL)}")
        logger.debug(f"DATABASE_URL set: {bool(self.DATABASE_URL)}")
        # Log only a sanitized version of the database URL (no credentials)
        db_url_display = self.database_url.split('@')[-1] if '@' in self.database_url else self.database_url[:30]
        logger.debug(f"Using database at: {db_url_display}")


@lru_cache()
def get_settings():
    return Settings()
