# AGENTS.md

## 1. Project Overview

**Repository:** `dsalazardev/ms-notifier-webhook`

**Repository state analyzed:** `main` at commit `6f19606d33bb5b1ec841f98b056e1db3af4e251f` (`feat(docs): add sdd framework`, 2026-09-22).

### Purpose

This repository contains a small Python microservice that exposes a versioned FastAPI webhook for receiving lead information from a landing page. The application validates the lead payload, schedules an in-process background task, downloads a file from Google Drive using a service-account credential, and sends that file as a PDF attachment through Azure Communication Services Email together with a configurable booking link.

The repository does **not** contain a database, queue, ORM/ODM, persistence module, authentication implementation, or visible deployment configuration for a specific cloud provider.

### Operational model

The active application flow is:

```text
HTTP request
  -> FastAPI router: /api/v1/lead
  -> Pydantic validation: LeadCreate
  -> FastAPI BackgroundTasks
  -> process_lead_pipeline()
      -> AsyncDriveService.get_pdf_bytes()
          -> Google service-account credentials
          -> Google Drive API
      -> AsyncEmailService.send_lead_email()
          -> Azure Communication Services Email
          -> PDF attachment encoded as Base64
```

The caller receives the webhook response before the lead-processing pipeline completes. Processing failures are logged inside the background task and are not returned to the original HTTP caller.

### Naming currently observable in code

There are several service-name variants that should not be silently normalized during unrelated changes:

- Repository: `ms-notifier-webhook`
- Python project package: `ms-notifier-webhook`
- FastAPI title: `ms-notifier-webhook` (unificado en el change `ms-notifier-hardening`)
- FastAPI description: `Microservicio asíncrono para despachar recursos y correos a leads.`
- Health endpoint service field: `ms-notifier-webhook` (unificado en el change `ms-notifier-hardening`)

El naming quedó unificado en `ms-notifier-webhook` por el change `ms-notifier-hardening`.

---

## 2. Repository Structure

Tracked repository contents consist of 65 files across 41 directories at the analyzed `main` commit.

### Application tree

```text
src/
├── __init__.py
├── main.py
├── api/
│   ├── __init__.py
│   └── webhook.py
├── core/
│   ├── __init__.py
│   ├── config.py
│   └── exceptions.py
├── models/
│   ├── __init__.py
│   └── lead.py
└── services/
    ├── __init__.py
    ├── drive_service.py
    └── email_service.py
```

### Repository-support files

```text
.
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── README.md
├── conftest.py
├── pyproject.toml
├── uv.lock
├── tests/
├── .claude/
├── .github/
└── .opencode/
```

`.idea/` ya no está trackeado (change `ms-notifier-hardening`) y está en `.gitignore`.

### OpenSpec / coding-agent support

The repository contains OpenSpec tooling in three integration-oriented locations:

```text
.claude/
├── commands/opsx/*.md
└── skills/openspec-*/SKILL.md

.github/
├── agents/openspec.agent.md
├── prompts/opsx-*.prompt.md
├── skills/openspec-*/SKILL.md
└── workflows/copilot-setup-steps.yml

.opencode/
├── commands/opsx-*.md
└── skills/openspec-*/SKILL.md

openspec/
├── config.yaml
├── changes/
│   └── archive/.gitkeep
└── specs/
    └── .gitkeep
```

These trees provide OpenSpec workflows for multiple AI/coding-agent environments. They are project tooling, not runtime application code.

### IDE configuration

`.idea/` is tracked and contains PyCharm/JetBrains project metadata. `ms-notifier-webhook.iml` marks `src/` as the source folder and excludes `.venv/`. The committed IDE configuration also contains a machine-specific Windows/OneDrive Python SDK path. Do not use that path as a portable project instruction.

### Files absent from the repository

No `README.md`, test directory, test module, CI test workflow, deployment manifest, database migration directory, seed directory, or application-level documentation directory is present in the tracked tree at the analyzed commit.

Do not infer missing artifacts from common Python project conventions.

---

## 3. Technology Stack

### Runtime and language

- Python `>=3.14` declared in `pyproject.toml` and `uv.lock`.
- Docker base image: `python:3.14-slim`.
- `uv` is used for dependency installation and is copied into the image from `ghcr.io/astral-sh/uv:latest`.

### Application framework

- FastAPI: declared `>=0.115.0`, locked `0.141.1`.
- Uvicorn: declared `>=0.32.0`, locked `0.53.0`.
- Pydantic: declared through `pydantic[email]>=2.9.2`, locked `2.13.5`.
- Pydantic Settings: `>=2.5.2`, locked `2.15.0`.

### External-service libraries

- `httpx`: declared `>=0.28.0`, locked `0.28.1`; used for Google Drive HTTP download.
- `google-auth`: declared `>=2.35.0`, locked `2.58.0`; used for service-account credentials and token refresh.
- `slowapi`: declared `>=0.1.9`; used for per-IP rate limiting on `/lead`.
- `azure-communication-email`: declared `>=1.1.0`, locked `1.1.0`; used for asynchronous email sending.
- `azure-core`: no longer a direct declaration; arrives transitively with the Azure SDK.

### Declared dependencies with no direct source-code usage found

Ya no aplica: `aiosmtplib`, `aiohttp` y `azure-core` (declaración explícita) fueron retiradas de `pyproject.toml` en el change `ms-notifier-hardening`. `azure-core` permanece como dependencia transitiva del SDK de Azure.

The commit history explicitly records a migration from SMTP to Azure Communication Services (`d108e6da9880637af1a4af0f91aeae3e5338821a`). Do not reintroduce SMTP behavior.

---

## 4. Architecture

The current repository implements a compact layered structure, although it is not a formal Clean Architecture or Hexagonal Architecture implementation.

```text
FastAPI application
│
├── src/main.py
│   └── application creation, CORS, router registration
│
├── src/api/webhook.py
│   └── HTTP boundary + orchestration entry point
│
├── src/models/lead.py
│   └── request validation / data contract
│
├── src/core/config.py
│   └── environment-backed application settings
│
├── src/core/exceptions.py
│   └── application-specific exception hierarchy
│
└── src/services/
    ├── drive_service.py
    │   └── Google Drive access
    └── email_service.py
        └── Azure Communication Services Email access
```

### Layer responsibilities observed

**`main.py`** owns application construction, CORS configuration, and router mounting.

**`api/webhook.py`** owns the HTTP endpoints and the application-level lead pipeline orchestration. It is the place where the Drive and email services are composed.

**`models/lead.py`** owns the validated input shape for a lead.

**`core/config.py`** owns environment loading and the conversion of the Google credential JSON string into a Python dictionary.

**`core/exceptions.py`** defines the controlled exception hierarchy for pipeline/service failures.

**`services/drive_service.py`** owns Google service-account authentication and file download.

**`services/email_service.py`** owns construction and sending of the Azure email message and attachment.

There is no separate domain layer, repository layer, controller class hierarchy, dependency-injection container, or persistence abstraction visible in the repository.

---

## 5. Core Application Flow

### `POST /api/v1/lead`

1. FastAPI receives the request at `/api/v1/lead`.
2. FastAPI/Pydantic validates the JSON body against `LeadCreate`.
3. `handle_lead()` schedules `process_lead_pipeline(lead)` using `BackgroundTasks`.
4. The endpoint returns `202 Accepted` with a JSON acceptance payload immediately.
5. The background task logs the start of processing.
6. `AsyncDriveService.get_pdf_bytes(settings.DRIVE_FILE_ID)` obtains a Google access token (refreshed only when invalid, off the event loop) and downloads the configured Drive file; the content is validated (`%PDF-` signature, size limit) and transient failures are retried with backoff by the orchestrator.
7. `AsyncEmailService.send_lead_email()` creates an email with:
   - sender from `FROM_EMAIL`;
   - recipient from `lead.email`;
   - `lead.need` interpolated into the body;
   - `BOOKING_URL` included in the body;
   - the downloaded bytes attached as `Documento_Especial.pdf` with content type `application/pdf`.
8. Azure Email is invoked using `EmailClient.from_connection_string(...)` and `begin_send(...)`.
9. The pipeline logs success with lead and phase; on definitive failure it sends an alert email to `ALERT_EMAIL` (fallback `FROM_EMAIL`) and never exposes errors to the HTTP caller.

### `GET /api/v1/health`

Returns a simple JSON health response with `status: ok` and service name `ms-notifier-webhook`.

### `GET /api/v1/health/ready`

Configuration-only readiness (no external calls): checks Google credentials JSON parseability, `DRIVE_FILE_ID`, Azure connection string, `CORS_ORIGINS`, `MAX_PDF_SIZE_MB` and `RATE_LIMIT_LEAD`. Responds 200 `ready` or 503 `not_ready` with a `checks` map.

The code comment on `/health` states that this endpoint is intended to keep the service alive through a Render cron-job ping. No Render-specific deployment configuration exists in the tracked repository, so that comment is the only repository evidence for the intended use.

---

## 6. Important Components

### `src/main.py`

Responsibilities:

- Creates the `FastAPI` application.
- Sets title, description, and version.
- Configures CORS.
- Mounts the webhook router under `/api/v1`.

Observed CORS configuration (post `bfd65f3`, hardened in `ms-notifier-hardening`):

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`CORS_ORIGINS` is a required JSON-array environment variable (allowlist). There is no wildcard. Changing CORS can alter frontend integration behavior.

### `src/api/webhook.py`

This is the main application orchestration module.

Important implementation facts:

- `AsyncDriveService()` is instantiated at module import time.
- `AsyncEmailService()` is instantiated at module import time.
- `settings` is imported from `src.core.config`.
- `process_lead_pipeline()` is the use-case-like orchestration function.
- `handle_lead()` is the webhook boundary.
- `health_check()` is the health endpoint.
- Logging is initialized with `logging.basicConfig(level=logging.INFO)` in this module.

Because service instances and `settings = Settings()` are created during import, configuration problems can prevent the module from importing at startup rather than only failing when a request arrives.

### `src/models/lead.py`

`LeadCreate` has exactly two required fields:

- `email: EmailStr`
- `need: str`

There are no defaults, optional fields, IDs, timestamps, or additional request metadata.

### `src/core/config.py`

`Settings` requires all seven declared application settings:

```text
GOOGLE_CREDENTIALS_JSON
DRIVE_FILE_ID
AZURE_COMMUNICATION_ENDPOINT
AZURE_COMMUNICATION_KEY
AZURE_EMAIL_CONNECTION_STRING
FROM_EMAIL
BOOKING_URL
```

`GOOGLE_CREDENTIALS_JSON` and `AZURE_EMAIL_CONNECTION_STRING` are `SecretStr` values.

Settings are loaded from `.env` using UTF-8 encoding.

`google_creds_dict` parses the secret string as JSON. Invalid JSON will fail when accessed.

### `src/core/exceptions.py`

Hierarchy:

```text
Exception
└── NotificationServiceError
    ├── DriveDownloadError
    └── EmailDeliveryError
```

The exception types are used to distinguish controlled Drive and email failures inside the pipeline.

### `src/services/drive_service.py`

Google Drive behavior:

- Uses the Drive read-only scope:
  `https://www.googleapis.com/auth/drive.readonly`
- Builds credentials from `service_account.Credentials.from_service_account_info(...)`.
- Refreshes the access token through `google.auth.transport.requests.Request()`.
- Downloads using `httpx.AsyncClient(timeout=30.0)`.
- Calls:
  `https://www.googleapis.com/drive/v3/files/{file_id}?alt=media`
- Sends the token as a Bearer authorization header.
- Calls `raise_for_status()`.
- Converts HTTP and unexpected failures into `DriveDownloadError`.

The method assumes the configured Drive file can be delivered as the PDF payload expected by the email service. No MIME-type or file-content validation is implemented here.

Note that `_get_access_token()` is synchronous and calls the credential refresh API from inside an otherwise asynchronous service. Treat this as an existing behavior and potential event-loop blocking point when making performance/concurrency changes.

### `src/services/email_service.py`

Azure Email behavior:

- Reads `AZURE_EMAIL_CONNECTION_STRING` as a secret.
- Creates `EmailClient` from the connection string.
- Uses the asynchronous Azure Email client.
- Sends through `begin_send(...)` and waits for the operation result.
- Treats `result.get("status") == "Failed"` as a delivery failure.
- Base64-encodes the PDF bytes before creating the attachment payload.
- Uses `settings.FROM_EMAIL` as sender.
- Uses `settings.BOOKING_URL` as the booking link.

The email body is currently hard-coded in Spanish and interpolates the recipient's email address into the greeting and the lead's `need` into the informational sentence.

The attachment is always represented as:

```text
name: Documento_Especial.pdf
contentType: application/pdf
```

The code catches `Exception` and wraps failures as `EmailDeliveryError`.

---

## 7. Configuration

### Configuration source

The application uses `pydantic-settings` with:

```python
SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

There is no separate configuration file or runtime configuration class elsewhere in the repository.

### Environment variables

| Variable | Purpose | Required evidence |
|---|---|---|
| `GOOGLE_CREDENTIALS_JSON` | JSON service-account credential used to authenticate against Google APIs. | Required: field has no default. |
| `DRIVE_FILE_ID` | Google Drive file identifier downloaded for every lead. | Required: field has no default. |
| `ALERT_EMAIL` | Optional alert recipient on definitive pipeline failure. | Optional; falls back to `FROM_EMAIL`. |
| `RATE_LIMIT_LEAD` | Per-IP rate limit for `/lead` (limits format). | Optional; default `5/minute`. |
| `MAX_PDF_SIZE_MB` | Maximum attached PDF size in MB. | Optional; default `10`. |
| `LOG_LEVEL` | Root logging level. | Optional; default `INFO`. |
| `AZURE_EMAIL_CONNECTION_STRING` | Connection string used to build the Azure `EmailClient`. | Required and directly used. |
| `FROM_EMAIL` | Sender address for outbound email. | Required and directly used. |
| `BOOKING_URL` | Booking link inserted into the email body. | Required and directly used. |

Never copy actual values from `.env` into source control or documentation.

`.env.example` is a template only. It contains placeholders for Azure, Google, and booking configuration.

### Configuration change rule

When introducing a new environment variable:

1. Add it to `Settings` in `src/core/config.py`.
2. Add a safe placeholder/documentation entry to `.env.example`.
3. Update every deployment/runtime instruction that is actually present and affected.
4. Do not expose real secrets.
5. Re-check any import-time behavior caused by `settings = Settings()`.

---

## 8. External Integrations

### Google Drive

**System:** Google Drive API v3.

**Authentication:** Google service-account JSON loaded from `GOOGLE_CREDENTIALS_JSON`.

**Scope:** Drive read-only.

**Operation:** direct HTTP GET to the Drive file media endpoint using `httpx`.

**Configuration:** `DRIVE_FILE_ID` and `GOOGLE_CREDENTIALS_JSON`.

**Error handling:** HTTP and unexpected exceptions are wrapped in `DriveDownloadError`.

There is no repository evidence of upload, write, delete, list, search, or update operations against Drive.

### Azure Communication Services Email

**System:** Azure Communication Services Email.

**SDK:** `azure-communication-email.aio`.

**Authentication/configuration used by current code:** `AZURE_EMAIL_CONNECTION_STRING`.

**Operation:** create an asynchronous `EmailClient`, submit the message with `begin_send`, await the result, and inspect the result status.

**Payload:** plain-text email plus Base64 PDF attachment.

**Error handling:** delivery failures and unexpected SDK errors become `EmailDeliveryError`.

### Booking provider

The application deliberately consumes a provider-neutral `BOOKING_URL`. Current source code does not integrate directly with Calendly, Cal.com, or another scheduling SDK/API. The booking system is represented only by a URL placed in the email.

The `.env.example` currently demonstrates a Calendly URL even though the setting name is provider-neutral. No code-level default booking provider was found.

---

## 9. API / Interfaces

Base path is `/api/v1`.

### `POST /api/v1/lead`

Request model:

```json
{
  "email": "prospect@example.com",
  "need": "string"
}
```

Validation is provided by `LeadCreate` / Pydantic, including `EmailStr` validation for `email`.

The success payload currently returned by the handler is:

```json
{
  "status": "accepted",
  "message": "Lead recibido y procesando"
}
```

There is no explicit `response_model` declaration.

The endpoint explicitly configures `status_code=202` since the `ms-notifier-hardening` change. Rate limiting applies per IP and returns `429` with `Retry-After` when exceeded.

### `GET /api/v1/health`

Response:

```json
{
  "status": "ok",
  "service": "ms-notifier-webhook"
}
```

### `GET /api/v1/health/ready`

Configuration-only readiness; responds 200 with `{"status": "ready", "checks": {...}}` or 503 with `{"status": "not_ready", "checks": {...}}`. No external calls are made.

No authentication or authorization mechanism is declared for these endpoints in the repository.

---

## 10. Data Flow

```text
Lead JSON
  │
  ├── email ───────────────┐
  │                         │
  └── need ─────────────┐   │
                         │   │
                  LeadCreate validation
                         │
                         ▼
                BackgroundTasks
                         │
                         ▼
               process_lead_pipeline
                         │
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
   DRIVE_FILE_ID                  lead.email/need
          │                             │
          ▼                             │
   Google Drive API                     │
          │                             │
          └────── PDF bytes ────────────┘
                         │
                         ▼
                  Azure Email
                         │
                         ├── FROM_EMAIL
                         ├── BOOKING_URL
                         └── PDF attachment
```

There is no persistent write between receiving the lead and sending the email. The repository contains no lead database or durable job record.

---

## 11. Testing

Since the `ms-notifier-hardening` change, the repository has a pytest suite under `tests/` plus a root `conftest.py` that sets dummy environment variables before importing `src` (no real Google/Azure calls).

Configuration lives in `pyproject.toml` (`[tool.pytest.ini_options]`, `asyncio_mode = "auto"`, `testpaths = ["tests"]`) and dev dependencies (`pytest`, `pytest-asyncio`, `ruff`) are declared in `[dependency-groups]`.

Commands:

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

CI runs lint, format check and tests on push/PR (`.github/workflows/ci.yml`).

### Agent rule

The suite is hermetic: never add tests that call Google Drive or Azure. Use mocks/monkeypatch and dummy env vars.

---

## 12. Code Quality and Conventions

### Confirmed conventions

- Python package imports use the absolute `src....` package path.
- Application code uses async functions for request/background/service operations.
- Service classes are named `AsyncDriveService` and `AsyncEmailService`.
- Application-specific exceptions are grouped in `src/core/exceptions.py`.
- Pydantic is used for request validation and settings.
- Logging uses the standard-library `logging` module.
- Source comments/docstrings are primarily written in Spanish.
- Commit history contains both conventional-style messages such as `feat(api): ...`, `fix(email): ...`, `refactor(config): ...`, and at least one free-form message (`changue name for lead`).

### Not configured / not evidenced

Ruff (lint + format) and pytest are configured since `ms-notifier-hardening` (see §11). There is still no mypy/type-checker, Sonar, pre-commit, or explicit commit-message enforcement.

Do not introduce additional mandatory tooling without an explicit project change that establishes it.

---

## 13. Development Commands

### Dependency installation / local environment

The repository declares `uv` as the package-management workflow and contains `uv.lock`.

The Dockerfile performs:

```bash
uv sync --frozen --no-dev --no-install-project
```

### Runtime

The Docker image starts the application with:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1
```

### Docker

Build context is configured with `.dockerignore` to exclude `.env`, secrets, virtual environments, IDE files, Git metadata, logs, and common caches.

The Dockerfile exposes port `8000` and runs a single Uvicorn worker.

### Commands not evidenced

Tests, lint and formatting commands now exist (see §11). No repository script explicitly documents commands for:

- type checking
- local debugging
- production migrations
- deployment

Do not invent these commands in future agent instructions unless they are added to the repository.

### Lockfile nuance

The Dockerfile installs with `uv sync --frozen` from `uv.lock`, so the container reproduces the locked dependency set. `uv lock --check` verifies lock/pyproject consistency.

---

## 14. Git / Development Workflow

The repository currently exposes only the `main` branch in the connected GitHub repository.

There are no pull requests visible in the repository search at the analyzed point.

Recent commits show this sequence of implementation evolution:

- initial communications microservice;
- SMTP-related work;
- migration to Azure Communication Services Email;
- `.env.example` introduction/update;
- lead naming change;
- booking-provider decoupling to `BOOKING_URL`;
- CORS middleware;
- OpenSpec/Solid/Summary documentation framework addition.

Because only `main` is visible and no branch naming standard is documented in the repository, do not invent a branch strategy in `AGENTS.md` or other repository documentation.

When making source changes, keep unrelated history/style cleanup separate from the functional change unless explicitly requested.

---

## 15. Security Considerations

Only document the controls actually visible in this repository.

### Secrets

- `GOOGLE_CREDENTIALS_JSON` uses `SecretStr`.
- `AZURE_COMMUNICATION_KEY` uses `SecretStr`.
- `AZURE_EMAIL_CONNECTION_STRING` is read through `SecretStr.get_secret_value()` and is ignored by `.gitignore` through `.env` exclusion.
- `.dockerignore` excludes `.env`, `.env.*`, `*.pem`, and `*.key` from the build context.

Do not log secret values or add them to tests, examples, or generated documentation.

### Input validation

Lead email validation uses `EmailStr` from Pydantic. The `need` field is required and typed as `str` but has no additional domain-specific validation.

### CORS

CORS is an explicit allowlist from `CORS_ORIGINS`; there is no wildcard. The landing's production domain must be added to `CORS_ORIGINS` or its preflight will be rejected (400). Behind a proxy, run uvicorn with `--proxy-headers`/`FORWARDED_ALLOW_IPS` so rate limiting sees the real client IP.

### Authentication / authorization

No authentication or authorization is implemented in the visible application code.

### Logging

The application logs lead email addresses and error messages. Consider this observable behavior when changing logging, error messages, or telemetry; do not add secrets to logs.

### Error exposure

The background pipeline logs exception messages rather than returning them to the lead caller. Avoid changing this error boundary accidentally, especially when modifying background-task execution.

This document is not a security audit; it records application behavior that is observable from the repository.

---

## 16. Critical Files

### CRITICAL

- `src/main.py` — application creation, middleware, router prefix.
- `src/api/webhook.py` — lead endpoint, background processing, service orchestration, logging.
- `src/core/config.py` — all runtime settings and import-time configuration.
- `src/services/drive_service.py` — Google authentication and file download contract.
- `src/services/email_service.py` — Azure email contract and attachment construction.
- `src/models/lead.py` — incoming webhook schema.
- `src/core/exceptions.py` — controlled service error types.
- `src/core/retry.py` — retry/backoff helper used by the pipeline.
- `src/core/rate_limit.py` — slowapi limiter instance.
- `src/core/logging.py` — logging configuration.

### IMPORTANT

- `pyproject.toml` — dependency declarations, Python version floor, Ruff/pytest config.
- `conftest.py` and `tests/` — hermetic pytest suite (dummy env vars, no network).
- `.github/workflows/ci.yml` — CI lint/format/tests on push and PR.
- `uv.lock` — resolved dependency set.
- `.env.example` — expected configuration keys and example placeholders.
- `Dockerfile` — runtime image, installation, port, and Uvicorn invocation.
- `.dockerignore` — build-context exclusions, including secret files.
- `openspec/config.yaml` — OpenSpec schema/cloud-agent configuration.
- `.github/workflows/copilot-setup-steps.yml` — GitHub Copilot setup workflow.
- `.github/agents/openspec.agent.md` — repository-supplied OpenSpec agent behavior.

### CONTEXTUAL

- `.gitignore` — repository artifact/secret/cache exclusions.
- `.idea/*` — IDE-only configuration; do not treat machine-specific paths as portable instructions.
- `.claude/**` — Claude-oriented OpenSpec commands/skills.
- `.github/prompts/**` and `.github/skills/**` — GitHub/Agent-oriented OpenSpec workflow material.
- `.opencode/**` — OpenCode-oriented OpenSpec commands/skills.
- `openspec/changes/**` and `openspec/specs/**` — currently empty placeholders except `.gitkeep` files.

---

## 17. Change Impact Areas

### API contract changes

```text
src/models/lead.py
    ↓
src/api/webhook.py
    ↓
frontend/webhook caller (external, not in this repo)
```

If request fields or validation rules change, inspect both `LeadCreate` and `handle_lead()` together.

### Lead-processing changes

```text
src/api/webhook.py
    ├── src/core/config.py
    ├── src/services/drive_service.py
    ├── src/services/email_service.py
    └── src/core/exceptions.py
```

### Google Drive changes

```text
src/core/config.py
    ↕
src/services/drive_service.py
    ↕
src/api/webhook.py
    ↕
src/core/exceptions.py
```

Check `GOOGLE_CREDENTIALS_JSON`, `DRIVE_FILE_ID`, credential scope, token refresh, URL construction, timeout, and exception mapping together.

### Email changes

```text
src/core/config.py
    ↕
src/services/email_service.py
    ↕
src/api/webhook.py
    ↕
src/core/exceptions.py
```

When changing providers, also inspect `pyproject.toml`, `uv.lock`, and `.env.example`.

### Environment/config changes

```text
src/core/config.py
    ↔
.env.example
    ↔
Docker/runtime environment
```

### Runtime/container changes

```text
pyproject.toml
uv.lock
Dockerfile
src/main.py
```

Check all four when changing Python/runtime dependencies or startup behavior.

---

## 18. Dependency Map

```text
src/main.py
  └── src.api.webhook
       ├── src.models.lead
       ├── src.services.drive_service
       │    ├── src.core.config
       │    └── src.core.exceptions
       ├── src.services.email_service
       │    ├── src.core.config
       │    └── src.core.exceptions
       └── src.core.config / exceptions
```

### Central modules

`src/api/webhook.py` is the central composition point. It depends on the model, configuration, exception hierarchy, and both external-provider services.

`src/core/config.py` is another high-impact module because it is loaded by both provider services and the API module and creates `settings` at import time.

### Peripheral modules

`src/models/lead.py`, `src/core/exceptions.py`, and provider-specific service modules are more focused, but changes to their public contracts still affect their direct callers.

---

## 19. Rules for AI Agents

1. **Read the relevant source before editing.** For lead-flow work, read `src/main.py`, `src/api/webhook.py`, `src/models/lead.py`, `src/core/config.py`, `src/core/exceptions.py`, `src/services/drive_service.py`, and `src/services/email_service.py` before making structural changes.

2. **Preserve the current responsibility boundaries.** HTTP concerns belong in `src/api/webhook.py`; request validation belongs in `src/models/`; environment parsing belongs in `src/core/config.py`; provider calls belong in `src/services/`; controlled exceptions belong in `src/core/exceptions.py`.

3. **Do not move provider logic into the route handler merely for convenience.** The current provider-specific logic is encapsulated in `AsyncDriveService` and `AsyncEmailService`.

4. **Treat `process_lead_pipeline()` as the orchestration point.** If a new step participates in the lead-processing sequence, inspect this function and preserve the existing ordering semantics.

5. **Remember that processing is background work.** A failure in Drive or email occurs after the HTTP handler schedules the task. Changing exception handling can change what the caller observes and whether failures are visible only through logs.

6. **Account for import-time initialization.** `settings`, `drive_service`, and `email_service` are initialized as modules are imported. Configuration or credential failures can therefore happen before the first request.

7. **Keep configuration synchronized.** When a setting changes, inspect both `src/core/config.py` and `.env.example`. Also inspect Docker/runtime configuration when the variable is needed in deployment.

8. **Never treat `.env.example` as a secret store.** Keep placeholders only. Never copy real credentials, private keys, access keys, or connection strings into source or documentation.

9. **Do not add scheduling-provider-specific code for `BOOKING_URL`.** The current application intentionally consumes a generic URL rather than an SDK integration.

10. **When touching email-provider dependencies, inspect historical leftovers.** `aiosmtplib` was removed from `pyproject.toml` in `ms-notifier-hardening`; the current implementation uses Azure Communication Services. Do not restore SMTP behavior without explicit requirements and a deliberate dependency/configuration change.

11. **When changing dependency declarations, check `pyproject.toml`, `uv.lock`, and `Dockerfile` together.** The lockfile is present, but the Docker install command currently uses `pyproject.toml` directly.

12. **Do not assume tests exist.** The current tracked repository contains no test suite. Do not claim a test passed unless an actual test command exists and was executed.

13. **Do not invent framework conventions.** There is no project-specific formatter/linter/type-checker configuration visible in the repository. Follow the existing code style unless introducing a tool is part of the requested change.

14. **Preserve public paths unless the change explicitly requires an API change.** Current public application routes are `/api/v1/lead` and `/api/v1/health`.

15. **Review CORS changes carefully.** `main.py` uses an explicit allowlist (`CORS_ORIGINS`); the wildcard was removed in `bfd65f3`. Any modification should be intentional and tested against the caller’s needs.

16. **Keep error taxonomy coherent.** Drive failures should remain distinguishable through `DriveDownloadError`; email failures through `EmailDeliveryError`; both inherit from `NotificationServiceError`.

17. **Do not silently broaden the external API surface.** There is currently no repository evidence of additional endpoints, webhooks, database APIs, queues, or event buses.

18. **Treat comments as context, not as overrides to executable behavior.** For example, the lead handler docstring says 202 Accepted, but the route decorator does not explicitly set that status. Verify actual code before documenting behavior.

19. **Preserve the provider-neutral booking abstraction.** The setting is `BOOKING_URL`. Do not rename it back to `CALENDLY_URL` or hard-code a provider unless the requested change explicitly changes that contract.

20. **Use OpenSpec when the requested workflow calls for it.** The repository is explicitly configured with `schema: spec-driven` and includes OpenSpec commands/skills for explore, propose, apply, update, sync, and archive workflows. Respect the planning/implementation boundary defined by those files.

21. **Before OpenSpec writes, check the project state.** The repository includes `openspec/config.yaml`, but `openspec/changes/` currently contains only an archive placeholder and `openspec/specs/` contains only a placeholder. Do not assume an active change exists.

22. **Do not use the three AI-tooling directories as runtime application code.** `.claude/`, `.github/` agent/prompt/skill files, and `.opencode/` are project-development tooling.

23. **Do not copy machine-specific IDE paths into portable instructions.** `.idea` is tracked but contains a user-specific Windows/OneDrive interpreter path.

24. **When modifying a central module, inspect its impact map before editing.** `src/api/webhook.py` and `src/core/config.py` are especially high-impact.

25. **Document newly discovered contradictions instead of hiding them.** This repository is small enough that configuration drift can directly affect runtime behavior.

---

## 20. Known Limitations / Inconsistencies

### API status mismatch (resolved)

`handle_lead()` now configures `status_code=202` explicitly (change `ms-notifier-hardening`); the docstring matches the behavior.

### Required-but-unused Azure settings (resolved)

`AZURE_COMMUNICATION_ENDPOINT` and `AZURE_COMMUNICATION_KEY` were removed from `Settings` (change `ms-notifier-hardening`); the email service only needs `AZURE_EMAIL_CONNECTION_STRING`. Legacy values in `.env` are ignored (`extra="ignore"`).

### Legacy email dependency declarations (resolved)

`aiosmtplib`, `aiohttp` and the explicit `azure-core` declaration were removed from `pyproject.toml` (change `ms-notifier-hardening`).

### Lockfile / Docker installation ambiguity (resolved)

The Dockerfile now installs with `uv sync --frozen` from `uv.lock` and runs as non-root (`appuser`) with a HEALTHCHECK (change `ms-notifier-hardening`).

### Booking example drift

`BOOKING_URL` is provider-neutral, while `.env.example` demonstrates a Calendly URL. The current code has no provider-specific booking client and no code-level default booking URL.

### Synchronous connection-string parsing (documented, not moved)

`EmailClient.from_connection_string` is synchronous but performs no network I/O (it only parses the string). It intentionally stays inside the send path to avoid failing at import time; moving it to `__init__` is not required (H17).

### CORS permissiveness (resolved)

CORS is an explicit allowlist from `CORS_ORIGINS`; the wildcard was removed in `bfd65f3` and there is no permissive fallback.

### Synchronous credential refresh in async service (resolved)

`_get_access_token()` now refreshes only when `creds.valid` is false, under an `asyncio.Lock`, and off the event loop via `asyncio.to_thread` (change `ms-notifier-hardening`).

### In-process background processing

The pipeline uses FastAPI `BackgroundTasks`. No durable queue, worker service, retry store, job table, or persistent processing state is present in the repository.

### No persistence

No database, cache, ORM/ODM, migration layer, or repository abstraction is present.

### No automated test suite (resolved)

A hermetic pytest suite, Ruff configuration and a GitHub Actions CI workflow exist since `ms-notifier-hardening` (see §11).

### No deployment manifest

The repository contains a Dockerfile and a health endpoint comment referencing Render, but no Render, Kubernetes, Terraform, Pulumi, AWS, Azure infrastructure, or other deployment manifest is present.

### IDE portability issue (resolved)

`.idea/` is no longer tracked and is ignored via `.gitignore` (change `ms-notifier-hardening`).

---

## 21. What Agents Must Verify Before Changes

Before changing **any application behavior**, verify:

- the target file’s current implementation;
- its direct imports and callers;
- relevant environment variables in `src/core/config.py`;
- related exceptions in `src/core/exceptions.py`;
- the affected external provider service;
- whether the API contract or background-task semantics change;
- whether `.env.example`, `pyproject.toml`, `uv.lock`, or `Dockerfile` must change with it.

### Before changing the webhook contract

Read:

```text
src/main.py
src/api/webhook.py
src/models/lead.py
```

Verify route prefix, HTTP method/path, validation, response payload, and background-task behavior.

### Before changing Drive behavior

Read:

```text
src/services/drive_service.py
src/core/config.py
src/core/exceptions.py
src/api/webhook.py
```

Verify file ID, credential scope, token flow, timeout, HTTP endpoint, and exception mapping.

### Before changing email behavior

Read:

```text
src/services/email_service.py
src/core/config.py
src/core/exceptions.py
src/api/webhook.py
pyproject.toml
.env.example
uv.lock
```

Verify sender, recipient, content, booking link, attachment encoding, Azure client lifecycle, error mapping, and dependencies.

### Before changing startup/container behavior

Read:

```text
src/main.py
src/core/config.py
Dockerfile
.dockerignore
pyproject.toml
uv.lock
```

Verify Python version, package installation, environment requirements, exposed port, Uvicorn target, worker count, and build context.

### Before adding tests/tooling

First confirm the current repository has no test/lint/type-check configuration. Establish the requested tool explicitly rather than pretending an existing project convention exists.

### Before changing OpenSpec workflows

Read:

```text
openspec/config.yaml
.github/agents/openspec.agent.md
.github/prompts/
.github/skills/
```

and the corresponding `.claude/` / `.opencode/` workflow file when the target agent environment matters.

---

## 22. Evidence / Source of Truth

For repository work, use the following evidence order:

1. Current executable/source code in `src/`.
2. Current configuration (`pyproject.toml`, `src/core/config.py`, `Dockerfile`, `.env.example`, `uv.lock`).
3. Current OpenSpec configuration/workflow files.
4. Existing tests/scripts, when present.
5. Documentation/comments and commit history as contextual evidence.

When sources disagree, do not hide the discrepancy. Record which source says what and prefer the current executable/configuration behavior when documenting the observed runtime design.

### Primary evidence map

```text
Project identity / dependencies
  -> pyproject.toml
  -> uv.lock

Application startup
  -> src/main.py

HTTP API / orchestration
  -> src/api/webhook.py

Lead validation
  -> src/models/lead.py

Configuration
  -> src/core/config.py
  -> .env.example

Error taxonomy
  -> src/core/exceptions.py

Google Drive integration
  -> src/services/drive_service.py

Azure email integration
  -> src/services/email_service.py

Container/runtime
  -> Dockerfile
  -> .dockerignore

OpenSpec
  -> openspec/config.yaml
  -> .github/agents/openspec.agent.md
  -> .github/workflows/copilot-setup-steps.yml
  -> .claude/**
  -> .github/prompts/**
  -> .github/skills/**
  -> .opencode/**

Git/repository history
  -> GitHub commit history on `main`
```

### Important evidence constraints

Do not infer:

- a database from lead data;
- a queue from `BackgroundTasks`;
- a scheduling provider integration from a booking URL;
- an authentication system from secret settings;
- a production deployment platform from the Render comment alone;
- an automated test strategy from pytest-related ignore patterns;
- a branch naming convention from a single GitHub branch;
- a default `BOOKING_URL` from `.env.example`; it is an example value, not a code default.

When something cannot be established from the repository, state:

```text
No determinado a partir del repositorio.
```

or:

```text
No existe evidencia suficiente en el repositorio para afirmarlo.
```

---

## 23. Working Checklist for Agents

### Before editing

- [ ] Read this `AGENTS.md`.
- [ ] Identify the actual entry point and affected modules.
- [ ] Read the relevant source/config files completely.
- [ ] Check for relevant OpenSpec change artifacts when the requested workflow uses OpenSpec.
- [ ] Identify environment variables and external integrations involved.

### During editing

- [ ] Keep responsibilities aligned with the existing module boundaries.
- [ ] Preserve `/api/v1/lead` and `/api/v1/health` unless the change explicitly modifies the API.
- [ ] Preserve background-task semantics unless the change explicitly targets delivery behavior.
- [ ] Update `.env.example` for new settings.
- [ ] Keep dependency declarations and lockfile consistent when dependencies change.
- [ ] Do not introduce undocumented infrastructure assumptions.
- [ ] Do not add secrets or real credentials.

### Before finishing

- [ ] Review affected files for accidental contract changes.
- [ ] Verify the new behavior using repository-supported commands or targeted runtime checks.
- [ ] Do not claim tests/lint/formatting were executed when no such project command exists.
- [ ] Record relevant limitations or contradictions introduced/resolved by the change.
- [ ] When using OpenSpec, validate the relevant artifacts according to the repository’s OpenSpec workflow.

---

## 24. Current Repository Snapshot

At the analyzed `main` commit:

- Application source is concentrated in 15 Python files under `src/` (including package `__init__.py` files).
- The application is a single FastAPI service with three HTTP routes.
- Lead handling is asynchronous only in the sense of FastAPI async/background execution; there is no separate worker service.
- Google Drive is the source of the attached document.
- Azure Communication Services Email is the active email provider in current source code.
- Booking is represented by the configurable `BOOKING_URL` only.
- There is no visible database or persistence layer.
- There is a hermetic pytest suite and a CI workflow since `ms-notifier-hardening`.
- There is no visible deployment manifest beyond the Dockerfile.
- OpenSpec is explicitly configured and repository tooling is committed for several AI-agent environments.

This section is a snapshot, not a permanent guarantee. Future changes may invalidate it; agents must re-check the repository when the codebase changes significantly.
