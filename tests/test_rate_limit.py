from src.core.config import settings
from src.core.rate_limit import limiter

PAYLOAD = {"email": "lead@example.com", "need": "modernizar"}


def test_rate_limit_returns_429_with_retry_after(client, mock_pipeline, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_LEAD", "2/minute")

    assert client.post("/api/v1/lead", json=PAYLOAD).status_code == 202
    assert client.post("/api/v1/lead", json=PAYLOAD).status_code == 202

    response = client.post("/api/v1/lead", json=PAYLOAD)
    assert response.status_code == 429
    assert response.headers.get("Retry-After")
    assert mock_pipeline.call_count == 2


def test_health_endpoints_are_not_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_LEAD", "1/minute")

    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/health/ready").status_code == 200


def test_rate_limit_is_configurable(client, mock_pipeline, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_LEAD", "1/minute")
    assert client.post("/api/v1/lead", json=PAYLOAD).status_code == 202
    assert client.post("/api/v1/lead", json=PAYLOAD).status_code == 429

    monkeypatch.setattr(settings, "RATE_LIMIT_LEAD", "3/minute")
    limiter.reset()
    assert client.post("/api/v1/lead", json=PAYLOAD).status_code == 202


def test_preflight_does_not_consume_rate_limit_quota(client, mock_pipeline, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_LEAD", "1/minute")

    preflight = client.options(
        "/api/v1/lead",
        headers={
            "Origin": "http://localhost:4321",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers.get("access-control-allow-origin") == "http://localhost:4321"

    assert client.post("/api/v1/lead", json=PAYLOAD).status_code == 202
    assert mock_pipeline.call_count == 1


def test_cors_preflight_allows_listed_origin_and_rejects_others(client):
    allowed = client.options(
        "/api/v1/lead",
        headers={
            "Origin": "http://localhost:4321",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:4321"

    rejected = client.options(
        "/api/v1/lead",
        headers={
            "Origin": "https://not-allowed.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers
