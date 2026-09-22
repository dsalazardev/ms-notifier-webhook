import json

from pydantic import EmailStr, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GOOGLE_CREDENTIALS_JSON: SecretStr
    DRIVE_FILE_ID: str

    AZURE_EMAIL_CONNECTION_STRING: SecretStr

    FROM_EMAIL: str
    ALERT_EMAIL: EmailStr | None = None

    BOOKING_URL: str

    CORS_ORIGINS: list[str]

    RATE_LIMIT_LEAD: str = "5/minute"
    MAX_PDF_SIZE_MB: int = 10
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def google_creds_dict(self) -> dict:
        return json.loads(self.GOOGLE_CREDENTIALS_JSON.get_secret_value())


settings = Settings()
