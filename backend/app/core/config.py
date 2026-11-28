from datetime import timedelta
from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MINIMUM_JWT_SECRET_LENGTH = 32


class Environment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Environment = Environment.LOCAL
    log_level: LogLevel = LogLevel.INFO
    log_json: bool = False

    database_url: str = Field(min_length=1)
    redis_url: str = Field(min_length=1)

    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = Field(default=15, gt=0)
    refresh_token_ttl_days: int = Field(default=30, gt=0)
    password_reset_token_ttl_minutes: int = Field(default=60, gt=0)
    cookie_secure: bool = False

    frontend_password_reset_url: str = "http://localhost:3000/nowe-haslo"

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_use_tls: bool = False
    mail_from: str = "AutoServis <no-reply@autoservis.local>"

    sentry_dsn: str | None = None

    demo_user_password: SecretStr | None = None

    booking_lead_time_minutes: int = Field(default=60, ge=0)
    booking_horizon_days: int = Field(default=60, gt=0)
    client_cancellation_deadline_hours: int = Field(default=12, ge=0)
    appointment_reminder_hours: int = Field(default=24, gt=0)

    realtime_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    realtime_ticket_ttl_seconds: int = Field(default=30, gt=0)
    order_board_closed_days: int = Field(default=7, gt=0)

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_length(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < MINIMUM_JWT_SECRET_LENGTH:
            message = f"JWT secret key must have at least {MINIMUM_JWT_SECRET_LENGTH} characters"
            raise ValueError(message)
        return value

    @property
    def access_token_ttl(self) -> timedelta:
        return timedelta(minutes=self.access_token_ttl_minutes)

    @property
    def refresh_token_ttl(self) -> timedelta:
        return timedelta(days=self.refresh_token_ttl_days)

    @property
    def password_reset_token_ttl(self) -> timedelta:
        return timedelta(minutes=self.password_reset_token_ttl_minutes)

    @property
    def booking_lead_time(self) -> timedelta:
        return timedelta(minutes=self.booking_lead_time_minutes)

    @property
    def client_cancellation_deadline(self) -> timedelta:
        return timedelta(hours=self.client_cancellation_deadline_hours)

    @property
    def appointment_reminder_window(self) -> timedelta:
        return timedelta(hours=self.appointment_reminder_hours)


@lru_cache
def get_settings() -> Settings:
    return Settings()
