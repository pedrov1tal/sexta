from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "KitchenCheck"
    environment: str = "development"
    database_url: str = "sqlite:///./data/kitchencheck.db"
    log_level: str = "INFO"
    admin_api_key: SecretStr = SecretStr("")
    operation_timezone: str = "America/Sao_Paulo"

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
