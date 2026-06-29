# backend/config.py
"""
ArthAI Configuration — loads all settings from environment variables.
Uses pydantic-settings for validation and type coercion.
Validates critical vars on import — crashes fast if missing.
"""
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings
from typing import Optional, List
import sys
import os


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./arthai_demo.db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def convert_postgres_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # AI APIs
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL_VISION: str = "gpt-4o-mini"
    OPENAI_MODEL_NLU: str = "gpt-4o-mini"
    SARVAM_API_KEY: Optional[str] = None
    SARVAM_ASR_MODEL: str = "saarika-v2"

    # Sahamati Account Aggregator (AA) Settings
    SAHAMATI_CLIENT_ID: str = ""
    SAHAMATI_CLIENT_SECRET: str = ""
    SAHAMATI_SANDBOX: bool = True


    # Messaging
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886"
    TWILIO_WEBHOOK_URL: str = "http://localhost:8000/webhook/whatsapp"
    WEBHOOK_SKIP_VERIFY: bool = False

    # Meta WhatsApp Business API (WABA) Settings
    WHATSAPP_PROVIDER: str = "twilio_sandbox"  # "twilio_sandbox" | "twilio_waba" | "meta_direct"
    META_WHATSAPP_TOKEN: str = ""
    META_PHONE_NUMBER_ID: str = ""
    META_VERIFY_TOKEN: str = ""


    # Storage
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_BUCKET_NAME: str = "arthai-receipts"
    AWS_REGION: str = "ap-south-1"

    # App
    SECRET_KEY: str = "arthai-dev-secret-key-change-in-production"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    SENTRY_DSN: Optional[str] = None

    # Feature flags
    ENABLE_SARVAM_ASR: bool = False
    ENABLE_S3_STORAGE: bool = False
    CONFIDENCE_THRESHOLD: float = 0.85
    DEMO_MODE: bool = True

    ARTHASCORE_MIN: int = 300
    ARTHASCORE_MAX: int = 900

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if self.DEMO_MODE:
                raise ValueError("DEMO_MODE cannot be enabled in production environment.")
            if self.SECRET_KEY == "arthai-dev-secret-key-change-in-production":
                raise ValueError("SECRET_KEY must be changed to a secure value in production environment.")
        return self

    model_config = {
        "env_file": os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    def validate_critical(self):
        """Raise error in production or warn in demo/dev if critical env vars are missing."""
        critical = [
            ("OPENAI_API_KEY", self.OPENAI_API_KEY),
            ("TWILIO_ACCOUNT_SID", self.TWILIO_ACCOUNT_SID),
        ]
        missing = [name for name, val in critical if not val or "your_" in str(val)]
        if missing:
            if self.ENVIRONMENT == "production":
                raise ValueError(f"Missing critical production environment variables: {missing}")
            else:
                print(f"⚠️  WARNING: Missing environment variables: {missing}")
                print("Copy .env.example → .env and fill in the required values.")

        if self.ENABLE_SARVAM_ASR and not self.SARVAM_API_KEY:
            if self.ENVIRONMENT == "production":
                raise ValueError("ENABLE_SARVAM_ASR=true but SARVAM_API_KEY not set in production.")
            else:
                print("⚠️  WARNING: ENABLE_SARVAM_ASR=true but SARVAM_API_KEY not set.")
                print("   Voice will fall back to OpenAI Whisper.")


settings = Settings()
settings.validate_critical()

