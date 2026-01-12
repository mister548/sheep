"""Конфигурация приложения."""
import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения."""

    # Telegram Bot
    BOT_TOKEN: str

    # Database
    DATABASE_URL: str

    # Gen API
    GEN_API_URL: str
    GEN_API_KEY: str
    CALLBACK_URL: str

    # YooKassa
    YOOKASSA_SHOP_ID: str
    YOOKASSA_SECRET_KEY: str
    YOOKASSA_WEBHOOK_URL: str

    # Bot settings
    BOT_USERNAME: str
    START_CREDITS: int = 10
    GENERATION_COST: int = 2

    # FastAPI
    WEBHOOK_SECRET: Optional[str] = None
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


