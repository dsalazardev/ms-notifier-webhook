import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from src.core.config import settings
from src.core.exceptions import DocumentValidationError
from src.services.drive_service import AsyncDriveService, validate_pdf_bytes
from src.services.email_service import build_alert_message, build_lead_message

PDF = b"%PDF-1.7 contenido"
MAX_BYTES = 1024


def test_validate_pdf_accepts_valid_document():
    validate_pdf_bytes(PDF, max_bytes=MAX_BYTES, content_length=len(PDF))


def test_validate_pdf_rejects_non_pdf():
    with pytest.raises(DocumentValidationError):
        validate_pdf_bytes(b'{"error": "not found"}', max_bytes=MAX_BYTES)


def test_validate_pdf_rejects_oversize_by_real_size():
    with pytest.raises(DocumentValidationError):
        validate_pdf_bytes(b"%PDF-1.7" + b"x" * MAX_BYTES, max_bytes=MAX_BYTES)


def test_validate_pdf_rejects_oversize_by_content_length():
    with pytest.raises(DocumentValidationError):
        validate_pdf_bytes(PDF, max_bytes=MAX_BYTES, content_length=MAX_BYTES + 1)


class FakeResponse:
    def __init__(self, content, headers=None):
        self.content = content
        self.headers = headers or {}

    def raise_for_status(self):
        return None


class FakeAsyncClient:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, headers=None):
        return self._response


def _service_with_fake_http(monkeypatch, response):
    service = AsyncDriveService()
    monkeypatch.setattr(service, "_get_access_token", AsyncMock(return_value="token"))
    monkeypatch.setattr(
        "src.services.drive_service.httpx.AsyncClient",
        lambda **kwargs: FakeAsyncClient(response),
    )
    return service


async def test_get_pdf_bytes_returns_valid_pdf(monkeypatch):
    response = FakeResponse(PDF, {"content-length": str(len(PDF))})
    service = _service_with_fake_http(monkeypatch, response)
    assert await service.get_pdf_bytes("file-id") == PDF


async def test_get_pdf_bytes_rejects_non_pdf(monkeypatch):
    response = FakeResponse(b'{"error": "not found"}')
    service = _service_with_fake_http(monkeypatch, response)
    with pytest.raises(DocumentValidationError):
        await service.get_pdf_bytes("file-id")


async def test_get_pdf_bytes_rejects_oversize(monkeypatch):
    monkeypatch.setattr(settings, "MAX_PDF_SIZE_MB", 1)
    response = FakeResponse(b"%PDF-1.7" + b"x" * (2 * 1024 * 1024))
    service = _service_with_fake_http(monkeypatch, response)
    with pytest.raises(DocumentValidationError):
        await service.get_pdf_bytes("file-id")


class FakeCreds:
    def __init__(self, valid):
        self.valid = valid
        self.token = "tok" if valid else None
        self.refresh_calls = 0

    def refresh(self, request):
        time.sleep(0.05)
        self.refresh_calls += 1
        self.valid = True
        self.token = "new-token"


async def test_token_is_not_refreshed_when_valid():
    service = AsyncDriveService()
    fake = FakeCreds(valid=True)
    service._creds = fake
    assert await service._get_access_token() == "tok"
    assert fake.refresh_calls == 0


async def test_token_refresh_is_single_under_concurrency():
    service = AsyncDriveService()
    fake = FakeCreds(valid=False)
    service._creds = fake
    tokens = await asyncio.gather(service._get_access_token(), service._get_access_token())
    assert tokens == ["new-token", "new-token"]
    assert fake.refresh_calls == 1


def test_build_lead_message_uses_neutral_greeting():
    message = build_lead_message("daner@example.com", "modernizar legacy", PDF)
    body = message["content"]["plainText"]
    assert "daner@example.com" not in body
    assert ".," not in body
    assert "modernizar legacy" in body
    assert settings.BOOKING_URL in body
    attachment = message["attachments"][0]
    assert attachment["name"] == "Checklist-27-puntos-SALAZAR-Eng.pdf"
    assert attachment["contentType"] == "application/pdf"


def test_build_alert_message_falls_back_to_from_email(monkeypatch):
    monkeypatch.setattr(settings, "ALERT_EMAIL", None)
    message = build_alert_message("lead@example.com", "drive.download", "boom")
    assert message["recipients"]["to"][0]["address"] == settings.FROM_EMAIL


def test_build_alert_message_uses_alert_email(monkeypatch):
    monkeypatch.setattr(settings, "ALERT_EMAIL", "alerts@example.com")
    message = build_alert_message("lead@example.com", "drive.download", "boom")
    assert message["recipients"]["to"][0]["address"] == "alerts@example.com"
