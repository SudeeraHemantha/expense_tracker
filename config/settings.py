"""
Central application settings and environment variables configuration.
Uses Pydantic BaseSettings and SettingsConfigDict.
"""

from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure environment variables from .env are explicitly loaded
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables or defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = Field(default="Expense Tracker API", description="Name of the application")
    APP_ENV: str = Field(default="development", description="Execution environment")
    DEBUG: bool = Field(default=True, description="Enable debug mode")

    BASE_DIR: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent,
        description="Base project directory"
    )
    DATA_DIR: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent / "data",
        description="Data storage directory"
    )
    DB_PATH: str = Field(
        default="sqlite:///./data/expenses.db",
        description="SQLite database path or connection URL"
    )
    DEFAULT_CURRENCY: str = Field(
        default="LKR",
        description="Default currency code"
    )
    CORS_ORIGINS: List[str] = Field(
        default=["*"],
        description="Allowed CORS origins"
    )
    ALERT_THRESHOLD_PERCENTAGE: float = Field(
        default=80.0,
        description="Budget alert warning threshold percentage"
    )

    # LLM API Key Settings
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        description="Google Gemini LLM API Key"
    )
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI LLM API Key"
    )

    # JWT Authentication & Token Security Settings
    SECRET_KEY: str = Field(
        default="expense_tracker_production_secret_key_antigravity_2026",
        description="Secret key for signing JWT tokens"
    )
    ALGORITHM: str = Field(
        default="HS256",
        description="Algorithm for JWT token signature"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="JWT Access Token expiration time in minutes (30 minutes)"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=30,
        description="JWT Refresh Token expiration time in days (30 days)"
    )

    @property
    def effective_db_path(self) -> str:
        """
        Return active database connection URL string.
        Automatically switches to writable /tmp directory when running in Vercel or serverless environments.
        """
        import os
        if os.getenv("VERCEL") or os.getenv("SERVERLESS") or os.getenv("NOW_BUILDER"):
            return "sqlite:////tmp/expenses.db"
        return self.DB_PATH

    def setup_directories(self) -> None:
        """Ensure necessary data storage directories exist."""
        import os
        if not (os.getenv("VERCEL") or os.getenv("SERVERLESS") or os.getenv("NOW_BUILDER")):
            try:
                self.DATA_DIR.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass


settings = Settings()
settings.setup_directories()
