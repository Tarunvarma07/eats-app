from pydantic import model_validator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict
)


class Settings(BaseSettings):

    DATABASE_URL: str

    JWT_SECRET_KEY: str

    ALGORITHM: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ALLOWED_ORIGINS: str = "http://localhost:8000"

    OFFICE_TIMEZONE: str = "Asia/Kolkata"

    LATE_LOGIN_HOUR: int = 9

    LATE_LOGIN_MINUTE: int = 30

    # Comma-separated CIDR ranges that are considered "office" IP space.
    # e.g. "192.168.1.0/24,10.0.0.0/8"
    # Leave blank (empty string) in dev environments → work_location = 'unknown'
    OFFICE_IP_RANGES: str = ""

    LOG_LEVEL: str = "INFO"

    @model_validator(mode="before")
    @classmethod
    def clean_env_prefixes(cls, data):
        if not isinstance(data, dict):
            return data
        cleaned = {}
        for key, val in data.items():
            if isinstance(val, str):
                prefix = f"{key}="
                if val.startswith(prefix):
                    val = val[len(prefix):]
            cleaned[key] = val
        return cleaned

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()