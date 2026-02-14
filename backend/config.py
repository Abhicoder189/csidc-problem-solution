"""
ILMCS Backend — Configuration
Environment-driven settings for all services.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── App ────────────────────────────────────────────────────────
    APP_NAME: str = "ILMCS"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me-in-production"

    # ── Database ───────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://ilmcs_admin:ilmcs_secure_2026@localhost:5432/ilmcs"

    # ── Google Earth Engine ────────────────────────────────────────
    GEE_SERVICE_ACCOUNT: str = ""
    GEE_PRIVATE_KEY_FILE: str = ""
    GEE_PROJECT: str = ""

    # ── Mapbox ─────────────────────────────────────────────────────
    MAPBOX_ACCESS_TOKEN: str = ""

    # ── Redis ──────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Paths ──────────────────────────────────────────────────────
    BASE_DIR: str = str(Path(__file__).resolve().parent)
    UPLOAD_DIR: str = str(Path(__file__).resolve().parent / "uploads")
    MODEL_DIR: str = str(Path(__file__).resolve().parent / "ai_models" / "weights")
    REPORTS_DIR: str = str(Path(__file__).resolve().parent / "reports")

    # ── ESRGAN ─────────────────────────────────────────────────────
    ESRGAN_MODEL_PATH: str = ""
    ESRGAN_SCALE_FACTOR: int = 4

    # ── CORS ───────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
