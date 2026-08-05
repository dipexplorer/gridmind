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
        """Construct the PostgreSQL connection string from individual parts, or use override."""
        import os
        env_url = os.getenv("DATABASE_URL")
        if env_url:
            return env_url
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
    # CORS_ORIGINS is a comma-separated string in .env
    CORS_ORIGINS: str = "*"

    # ─── File Uploads ─────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_TEMP_DIR: str = "/tmp/gridmind_uploads"

    # ─── ML Models ────────────────────────────────────────────────────────────
    MODEL_DIR: str = "ml_models"
    # DEPRECATED for Isolation Forest training.
    # IF now uses contamination="auto" (sklearn default heuristic) so that
    # the known label distribution (12.13% anomalies) is NOT injected directly
    # into the model threshold — which would make evaluation artificially easy.
    # Retained here for any legacy callers or future override via .env.
    ANOMALY_CONTAMINATION: float = 0.12

    # Fusion weights for Health Score calculation
    HEALTH_WEIGHT_IF: float = 0.25
    HEALTH_WEIGHT_XGB: float = 0.35
    HEALTH_WEIGHT_COX: float = 0.25
    HEALTH_WEIGHT_PHYSICS: float = 0.15

    # Physics nominal limits
    NOMINAL_VOLTAGE: float = 415.0
    TEMPERATURE_LIMIT_CRITICAL: float = 85.0
    TEMPERATURE_LIMIT_WARNING: float = 70.0
    LOAD_LIMIT_CRITICAL: float = 115.0
    LOAD_LIMIT_WARNING: float = 90.0
    VOLTAGE_LIMIT_CRITICAL: float = 380.0
    VOLTAGE_LIMIT_WARNING: float = 395.0

    # Telemetry validation bounds (reject readings outside these limits)
    TEMP_MIN_VALID: float = -10.0
    TEMP_MAX_VALID: float = 160.0
    VOLTAGE_MIN_VALID: float = 200.0
    VOLTAGE_MAX_VALID: float = 500.0
    CURRENT_MIN_VALID: float = 0.0
    CURRENT_MAX_VALID: float = 10000.0
    LOAD_MIN_VALID: float = 0.0
    LOAD_MAX_VALID: float = 200.0

    # Default transformer metadata used when DB columns are NULL
    DEFAULT_AGE_YEARS: int = 10
    DEFAULT_RATED_KVA: float = 500.0

    # Batch job settings
    BATCH_COMMIT_EVERY: int = 100   # commit every N transformers

    class Config:
        env_file = ".env"            # Load from .env file if it exists
        env_file_encoding = "utf-8"
        case_sensitive = False       # POSTGRES_HOST == postgres_host
        extra = "ignore"             # Allow extra environment variables like PYTHONPATH


# Singleton — import this anywhere: from core.config import settings
settings = Settings()
