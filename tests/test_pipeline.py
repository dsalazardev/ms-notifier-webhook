import logging
from unittest.mock import AsyncMock

import pytest

from src.api.webhook import process_lead_pipeline
from src.core.exceptions import DriveDownloadError, EmailDeliveryError
from src.core.retry import run_with_retries
from src.models.lead import LeadCreate

PDF_BYTES = b"%PDF-1.7 test"
LEAD = LeadCreate(email="lead@example.com", need="modernizar")


async def fast_run(operation, **kwargs):
    kwargs.setdefault("sleep", AsyncMock())
    return await run_with_retries(operation, **kwargs)


@pytest.fixture
def no_retry_sleep(monkeypatch):
    monkeypatch.setattr("src.api.webhook.run_with_retries", fast_run)


@pytest.fixture
def drive_ok(monkeypatch):
    mock = AsyncMock(return_value=PDF_BYTES)
    monkeypatch.setattr("src.api.webhook.drive_service.get_pdf_bytes", mock)
    return mock


@pytest.fixture
def email_ok(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr("src.api.webhook.email_service.send_lead_email", mock)
    return mock


@pytest.fixture
def alert_mock(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr("src.api.webhook.email_service.send_alert_email", mock)
    return mock


async def test_retry_succeeds_on_second_attempt():
    sleeps = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    calls = {"n": 0}

    async def operation():
        calls["n"] += 1
        if calls["n"] < 2:
            raise DriveDownloadError("transient", retryable=True)
        return "ok"

    assert await run_with_retries(operation, sleep=fake_sleep) == "ok"
    assert calls["n"] == 2
    assert 0.375 <= sleeps[0] <= 0.625


async def test_permanent_error_is_not_retried():
    calls = {"n": 0}

    async def operation():
        calls["n"] += 1
        raise DriveDownloadError("permanent", retryable=False)

    with pytest.raises(DriveDownloadError):
        await run_with_retries(operation, sleep=AsyncMock())
    assert calls["n"] == 1


async def test_retries_are_exhausted_after_three_attempts():
    sleeps = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    calls = {"n": 0}

    async def operation():
        calls["n"] += 1
        raise DriveDownloadError("transient", retryable=True)

    with pytest.raises(DriveDownloadError):
        await run_with_retries(operation, sleep=fake_sleep)
    assert calls["n"] == 3
    assert len(sleeps) == 2
    assert 0.75 <= sleeps[1] <= 1.25


async def test_unknown_exception_is_not_retried_by_default():
    calls = {"n": 0}

    async def operation():
        calls["n"] += 1
        raise ValueError("nope")

    with pytest.raises(ValueError):
        await run_with_retries(operation, sleep=AsyncMock())
    assert calls["n"] == 1


async def test_pipeline_success(no_retry_sleep, drive_ok, email_ok, alert_mock):
    await process_lead_pipeline(LEAD)
    assert drive_ok.await_count == 1
    email_ok.assert_awaited_once_with(LEAD.email, LEAD.need, PDF_BYTES)
    assert alert_mock.await_count == 0


async def test_pipeline_retries_transient_drive_failure(
    no_retry_sleep, email_ok, alert_mock, monkeypatch
):
    calls = {"n": 0}

    async def flaky(file_id):
        calls["n"] += 1
        if calls["n"] == 1:
            raise DriveDownloadError("transient", retryable=True)
        return PDF_BYTES

    monkeypatch.setattr("src.api.webhook.drive_service.get_pdf_bytes", AsyncMock(side_effect=flaky))
    await process_lead_pipeline(LEAD)
    assert calls["n"] == 2
    assert email_ok.await_count == 1
    assert alert_mock.await_count == 0


async def test_pipeline_permanent_drive_failure_sends_alert(
    no_retry_sleep, email_ok, alert_mock, monkeypatch
):
    monkeypatch.setattr(
        "src.api.webhook.drive_service.get_pdf_bytes",
        AsyncMock(side_effect=DriveDownloadError("permanent", retryable=False)),
    )
    await process_lead_pipeline(LEAD)
    assert email_ok.await_count == 0
    alert_mock.assert_awaited_once()
    assert alert_mock.await_args.args[1] == "drive.download"


async def test_pipeline_exhausted_retries_send_alert(no_retry_sleep, alert_mock, monkeypatch):
    drive = AsyncMock(side_effect=DriveDownloadError("transient", retryable=True))
    monkeypatch.setattr("src.api.webhook.drive_service.get_pdf_bytes", drive)
    await process_lead_pipeline(LEAD)
    assert drive.await_count == 3
    assert alert_mock.await_count == 1


async def test_pipeline_email_failure_reports_email_phase(
    no_retry_sleep, drive_ok, alert_mock, monkeypatch
):
    monkeypatch.setattr(
        "src.api.webhook.email_service.send_lead_email",
        AsyncMock(side_effect=EmailDeliveryError("mail down", retryable=True)),
    )
    await process_lead_pipeline(LEAD)
    assert alert_mock.await_count == 1
    assert alert_mock.await_args.args[1] == "email.send"


async def test_pipeline_alert_failure_does_not_propagate(no_retry_sleep, drive_ok, monkeypatch):
    monkeypatch.setattr(
        "src.api.webhook.email_service.send_lead_email",
        AsyncMock(side_effect=EmailDeliveryError("mail down", retryable=True)),
    )
    monkeypatch.setattr(
        "src.api.webhook.email_service.send_alert_email",
        AsyncMock(side_effect=RuntimeError("alert down")),
    )
    await process_lead_pipeline(LEAD)


async def test_pipeline_logs_lead_and_phase(no_retry_sleep, alert_mock, monkeypatch, caplog):
    monkeypatch.setattr(
        "src.api.webhook.drive_service.get_pdf_bytes",
        AsyncMock(side_effect=DriveDownloadError("boom", retryable=False)),
    )
    caplog.set_level(logging.INFO, logger="src.api.webhook")
    await process_lead_pipeline(LEAD)
    assert "lead@example.com" in caplog.text
    assert "drive.download" in caplog.text
