import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Application configuration loaded from environment variables."""

    postgres_url: str
    jwt_secret: str
    jwt_expires_minutes: int
    cors_origins: List[str]


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Load settings from environment variables.

    Required env vars (ask orchestrator/user to set them in .env):
    - POSTGRES_URL
    - JWT_SECRET

    Optional:
    - JWT_EXPIRES_MINUTES (default 10080)
    - CORS_ORIGINS (comma-separated, default http://localhost:3000)
    """
    postgres_url = os.getenv("POSTGRES_URL", "").strip()
    jwt_secret = os.getenv("JWT_SECRET", "").strip()

    if not postgres_url:
        raise RuntimeError("Missing required env var POSTGRES_URL")
    if not jwt_secret:
        raise RuntimeError("Missing required env var JWT_SECRET")

    expires = int(os.getenv("JWT_EXPIRES_MINUTES", "10080"))
    cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    cors_origins = [x.strip() for x in cors_raw.split(",") if x.strip()]

    return Settings(
        postgres_url=postgres_url,
        jwt_secret=jwt_secret,
        jwt_expires_minutes=expires,
        cors_origins=cors_origins,
    )
