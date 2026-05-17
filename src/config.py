import os
from functools import lru_cache

from dotenv import find_dotenv, load_dotenv

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
        
        # Debug logging for deployment troubleshooting
        print(f"[CONFIG] API_KEY set: {bool(self.API_KEY)}")
        print(f"[CONFIG] POSTGRES_URI set: {bool(self.POSTGRES_URI)}")
        print(f"[CONFIG] POSTGRES_URL set: {bool(self.POSTGRES_URL)}")
        print(f"[CONFIG] DATABASE_URL set: {bool(self.DATABASE_URL)}")
        print(f"[CONFIG] Using database_url: {self.database_url[:30]}..." if len(self.database_url) > 30 else f"[CONFIG] Using database_url: {self.database_url}")


@lru_cache()
def get_settings():
    return Settings()
