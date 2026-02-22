"""Application configuration settings."""
from __future__ import annotations
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Deepfake Payment Gate"
    DEBUG: bool = False
    VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./payment_gate.db"

    # Redis (optional – falls back to in-memory)
    REDIS_URL: str = ""

    # Fiserv (optional)
    FISERV_BASE_URL: str = ""
    FISERV_CLIENT_ID: str = ""
    FISERV_CLIENT_SECRET: str = ""
    FISERV_MERCHANT_ID: str = ""

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Presage SmartSpectra
    PRESAGE_API_KEY: str = ""
    PRESAGE_GRPC_ENDPOINT: str = ""

    # OpenRouter (Arcee Trinity)
    OPENROUTER_API_KEY: str = ""

    # ElevenLabs
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"   # Rachel

    # Solana
    SOLANA_RPC_URL: str = ""
    SOLANA_PAYER_KEYPAIR: str = ""              # base-58 encoded secret key (64 bytes)

    # Challenge config
    CHALLENGE_TTL_SECONDS: int = 120
    CHALLENGE_MAX_RETRIES: int = 1

    # Risk thresholds
    RISK_AMOUNT_THRESHOLD: float = 1000.0
    RISK_VELOCITY_WINDOW_SECONDS: int = 600   # 10 min
    RISK_VELOCITY_MAX: int = 5

    @property
    def fiserv_configured(self) -> bool:
        return bool(self.FISERV_CLIENT_ID and self.FISERV_CLIENT_SECRET)

    @property
    def presage_configured(self) -> bool:
        return bool(self.PRESAGE_API_KEY)

    @property
    def gemini_configured(self) -> bool:
        return bool(self.GEMINI_API_KEY)

    @property
    def elevenlabs_configured(self) -> bool:
        return bool(self.ELEVENLABS_API_KEY)

    @property
    def solana_configured(self) -> bool:
        return bool(self.SOLANA_RPC_URL)


@lru_cache
def get_settings() -> Settings:
    return Settings()
