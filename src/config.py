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
    DATABASE_URL: str | None = os.getenv("DATABASE_URL")

    def __init__(self):
        # Use POSTGRES_URI first (Supabase), then DATABASE_URL (Render), then local default
        self.database_url = (
            self.POSTGRES_URI
            or self.DATABASE_URL
            or "postgresql+psycopg://localhost/group_project"
        )


@lru_cache()
def get_settings():
    return Settings()
