import json
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):
    GOOGLE_CREDENTIALS_JSON: SecretStr
    DRIVE_FILE_ID: str

    AZURE_COMMUNICATION_ENDPOINT: str
    AZURE_COMMUNICATION_KEY: SecretStr
    AZURE_EMAIL_CONNECTION_STRING: SecretStr

    FROM_EMAIL: str

    BOOKING_URL: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def google_creds_dict(self) -> dict:
        return json.loads(self.GOOGLE_CREDENTIALS_JSON.get_secret_value())


settings = Settings()