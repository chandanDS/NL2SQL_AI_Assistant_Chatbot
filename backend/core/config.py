from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Banking NL2SQL API"
    environment: Literal["development", "test", "production"] = "development"

    database_url: str = ""
    database_echo: bool = False
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=5, ge=0, le=40)
    database_connect_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    analytics_database_url: str = ""
    analytics_statement_timeout_ms: int = Field(default=10_000, ge=1_000, le=60_000)
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4.1-mini"
    openai_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    intent_confidence_threshold: float = Field(default=0.70, ge=0, le=1)

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_directory: Path = PROJECT_ROOT / "logs"
    log_filename: str = "banking_nl2sql.log"
    log_max_bytes: int = Field(default=5_242_880, ge=1_024)
    log_backup_count: int = Field(default=5, ge=1, le=20)
    log_to_console: bool = True
    synthetic_user_password: SecretStr = SecretStr("")
    jwt_secret_key: SecretStr = SecretStr("")
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_access_token_minutes: int = Field(default=30, ge=5, le=240)
    jwt_issuer: str = "banking-nl2sql-poc"
    jwt_audience: str = "banking-nl2sql-users"

    @property
    def log_file(self) -> Path:
        directory = self.log_directory
        if not directory.is_absolute():
            directory = PROJECT_ROOT / directory
        return directory / self.log_filename

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
