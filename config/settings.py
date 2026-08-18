"""
Central application settings and environment variables configuration.
Uses Pydantic BaseSettings and SettingsConfigDict.
"""

from pathlib import Path
from typing import List, Optional, Any
from dotenv import load_dotenv
from pydantic import Field, field_validator
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
    CORS_ORIGINS: Any = Field(
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

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, list):
            return v
        return ["*"]

    @property
    def effective_db_path(self) -> str:
        """
        Return active database connection URL string.
        Automatically switches to writable /tmp directory when running in Vercel or serverless environments.
        """
        import os
        if (
            os.getenv("VERCEL") or
            os.getenv("VERCEL_ENV") or
            os.getenv("AWS_LAMBDA_FUNCTION_NAME") or
            os.getenv("SERVERLESS") or
            os.getenv("NOW_BUILDER") or
            self.APP_ENV == "production"
        ):
            return "sqlite:////tmp/expenses.db"

        # Fallback check if local data directory is not writable
        try:
            self.DATA_DIR.mkdir(parents=True, exist_ok=True)
            return self.DB_PATH
        except Exception:
            return "sqlite:////tmp/expenses.db"

    def setup_directories(self) -> None:
        """Ensure necessary data storage directories exist when writable."""
        import os
        if not (os.getenv("VERCEL") or os.getenv("VERCEL_ENV") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("SERVERLESS")):
            try:
                self.DATA_DIR.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass


try:
    settings = Settings()
except Exception as _e:
    # Safe fallback if environment variable validation fails
    settings = Settings(_env_file=None)

settings.setup_directories()
