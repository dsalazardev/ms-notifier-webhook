import json
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):
    GOOGLE_CREDENTIALS_JSON: SecretStr
    DRIVE_FILE_ID: str

    SMTP_SERVER: str
    SMTP_PORT: int = 2525
    SMTP_USER: str
    SMTP_PASSWORD: SecretStr
    FROM_EMAIL: str

    CALENDLY_URL: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def google_creds_dict(self) -> dict:
        return json.loads(self.GOOGLE_CREDENTIALS_JSON.get_secret_value())


settings = Settings()