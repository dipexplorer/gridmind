"""
GridMind Configuration — Core Settings

This file reads ALL configuration from environment variables (or a .env file).
This is the 12-factor app pattern: "store config in the environment".

Why? Because the same code runs on:
  - Your laptop (localhost, test DB)
  - Production server (real DB, strong passwords)
...and you don't want passwords hardcoded in code.

Pydantic's BaseSettings automatically:
  1. Reads from environment variables
  2. Reads from .env file (as fallback)
  3. Validates types (e.g., ensures PORT is an integer, not a string)
"""
from pydantic_settings import BaseSettings
from typing import List
import urllib.parse


class Settings(BaseSettings):
    # ─── Database ─────────────────────────────────────────────────────────────
    # These are used to construct the DATABASE_URL connection string
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "gridmind"
    POSTGRES_USER: str = "gridmind_user"
    POSTGRES_PASSWORD: str = "changeme"

    @property
    def DATABASE_URL(self) -> str:
        """Construct the PostgreSQL connection string from individual parts."""
        encoded_password = urllib.parse.quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql://{self.POSTGRES_USER}:{encoded_password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ─── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ─── JWT Authentication ───────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "CHANGE_THIS_TO_A_256_BIT_RANDOM_STRING"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SUPABASE_JWT_SECRET: str = ""

    # ─── API ──────────────────────────────────────────────────────────────────
    API_DEBUG: bool = False
    # CORS_ORIGINS is a comma-separated string in .env, parsed into a list here
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # ─── File Uploads ─────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_TEMP_DIR: str = "/tmp/gridmind_uploads"

    # ─── ML Models ────────────────────────────────────────────────────────────
    MODEL_DIR: str = "ml_models"
    ANOMALY_CONTAMINATION: float = 0.05   # 5% of transformers expected to be anomalous

    class Config:
        env_file = ".env"            # Load from .env file if it exists
        env_file_encoding = "utf-8"
        case_sensitive = False       # POSTGRES_HOST == postgres_host


# Singleton — import this anywhere: from core.config import settings
settings = Settings()
