import os
from unittest.mock import AsyncMock

os.environ["GOOGLE_CREDENTIALS_JSON"] = (
    '{"type": "service_account", "project_id": "test-project", '
    '"private_key_id": "test-key-id", '
    '"private_key": "-----BEGIN PRIVATE KEY-----\\nMIIB\\n-----END PRIVATE KEY-----\\n", '
    '"client_email": "test@test-project.iam.gserviceaccount.com", "client_id": "1234567890"}'
)
os.environ["DRIVE_FILE_ID"] = "test-drive-file-id"
os.environ["AZURE_EMAIL_CONNECTION_STRING"] = (
    "endpoint=https://test.communication.azure.com/;accesskey=Zm9vYmFy"
)
os.environ["FROM_EMAIL"] = "noreply@example.com"
os.environ["BOOKING_URL"] = "https://booking.example.com/test"
os.environ["LEAD_EMAIL_LOGO_URL"] = "https://example.com/isotipo-white.png"
os.environ["LEAD_EMAIL_WHATSAPP_URL"] = "https://wa.me/573145919465"
os.environ["CORS_ORIGINS"] = '["http://localhost:4321"]'
os.environ["RATE_LIMIT_LEAD"] = "1000/minute"
os.environ["MAX_PDF_SIZE_MB"] = "10"
os.environ["LOG_LEVEL"] = "INFO"
os.environ["AZURE_COMMUNICATION_ENDPOINT"] = "https://legacy.example.com/"
os.environ["AZURE_COMMUNICATION_KEY"] = "legacy-key"

import pytest
from fastapi.testclient import TestClient

from src.core.rate_limit import limiter
from src.main import app


@pytest.fixture(autouse=True)
def reset_limiter():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_pipeline(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr("src.api.webhook.process_lead_pipeline", mock)
    return mock
