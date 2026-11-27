from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from datetime import time

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "KitchenCheck"
    environment: str = "development"
    database_url: str = "sqlite:///./data/kitchencheck.db"
    log_level: str = "INFO"
    admin_api_key: SecretStr = SecretStr("")
    operation_timezone: str = "America/Sao_Paulo"
    automation_interval_minutes: int = Field(default=1, ge=1)
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_chat_id: str = ""
    telegram_request_timeout_seconds: float = Field(default=10.0, gt=0)
    telegram_retry_attempts: int = Field(default=3, ge=1)
    telegram_retry_delay_seconds: float = Field(default=1.0, ge=0)
    telegram_daily_summary_time: time = time(23, 0)

    @field_validator("operation_timezone")
    @classmethod
    def validate_operation_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError(
                "OPERATION_TIMEZONE deve ser um fuso horário IANA válido."
            ) from error
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
