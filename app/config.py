from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "KitchenCheck"
    environment: str = "development"
    database_url: str = "sqlite:///./data/kitchencheck.db"
    log_level: str = "INFO"
    admin_api_key: SecretStr = SecretStr("")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
