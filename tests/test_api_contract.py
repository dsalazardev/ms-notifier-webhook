import logging

from pydantic import SecretStr

from src.core.config import Settings, settings
from src.core.logging import configure_logging

PAYLOAD = {"email": "lead@example.com", "need": "modernizar"}


def test_valid_payload_returns_202(client, mock_pipeline):
    response = client.post("/api/v1/lead", json=PAYLOAD)
    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted",
        "message": "Lead recibido y procesando",
    }
    assert mock_pipeline.call_count == 1


def test_necesidad_field_is_rejected(client, mock_pipeline):
    response = client.post(
        "/api/v1/lead",
        json={"email": "lead@example.com", "necesidad": "modernizar"},
    )
    assert response.status_code == 422
    assert mock_pipeline.call_count == 0


def test_invalid_email_is_rejected(client, mock_pipeline):
    response = client.post("/api/v1/lead", json={"email": "no-es-email", "need": "x"})
    assert response.status_code == 422
    assert mock_pipeline.call_count == 0


def test_missing_need_is_rejected(client, mock_pipeline):
    response = client.post("/api/v1/lead", json={"email": "lead@example.com"})
    assert response.status_code == 422
    assert mock_pipeline.call_count == 0


def test_health_returns_service_name(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ms-notifier-webhook"}


def test_readiness_ready_with_valid_config(client):
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert all(body["checks"].values())


def test_readiness_not_ready_with_invalid_google_credentials(client, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CREDENTIALS_JSON", SecretStr("no-es-json"))
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["google_credentials_json"] is False


def test_legacy_azure_variables_are_ignored():
    assert "AZURE_COMMUNICATION_ENDPOINT" not in Settings.model_fields
    assert "AZURE_COMMUNICATION_KEY" not in Settings.model_fields


def test_log_level_is_applied(monkeypatch):
    monkeypatch.setattr(settings, "LOG_LEVEL", "DEBUG")
    configure_logging()
    assert logging.getLogger().level == logging.DEBUG

    monkeypatch.undo()
    configure_logging()
    assert logging.getLogger().level == logging.INFO
