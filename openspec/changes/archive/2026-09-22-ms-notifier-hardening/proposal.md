# Proposal: ms-notifier-hardening

## Why

El microservicio que captura leads de la landing es un camino crítico de negocio con brechas de producción: no reintenta fallos transitorios ni alerta al dueño, no tiene rate limiting, no valida el PDF que adjunta, refresca el token de Google de forma síncrona en cada request, y su operación/calidad (tests, CI, docs, Docker) está sin endurecer. La exploración del 2026-09-22 (HEAD `bfd65f3`) documentó 19 hallazgos (H1–H19) verificados por QA cruzado; este primer change OpenSpec del backend resuelve 18 de ellos (H1, H3–H19) y deja H2 como configuración de despliegue pendiente del dueño.

## What Changes

- **Contrato y API (A)**: `POST /api/v1/lead` responde **202 Accepted explícito** (hoy 200 con docstring engañoso — **BREAKING** para consumidores que asuman 200); contrato canónico `{email: EmailStr, need: str}` documentado en spec (sin alias `necesidad`); naming unificado a `ms-notifier-webhook` en el título de FastAPI y en el campo `service` de `/health` (**BREAKING** menor del payload de health); nuevo `GET /api/v1/health/ready` (readiness solo de configuración, sin llamadas externas).
- **Resiliencia (B)**: retries con backoff exponencial (3 intentos) para errores transitorios de Drive/Azure y email de alerta al dueño (`ALERT_EMAIL` opcional con fallback) ante fallo definitivo; refresh del token de Google solo cuando `creds.valid` es falso, fuera del event loop (`asyncio.to_thread`) y con lock; validación del PDF descargado (magic bytes `%PDF-` y tamaño máximo `MAX_PDF_SIZE_MB`, default 10 MB) antes de adjuntar.
- **Seguridad (C)**: rate limiting por IP en `/lead` con `RATE_LIMIT_LEAD` (default `5/minute`) y respuesta 429 con `Retry-After`; limpieza de `Settings` retirando `AZURE_COMMUNICATION_ENDPOINT` y `AZURE_COMMUNICATION_KEY` (variables legacy toleradas sin efecto, `extra="ignore"`).
- **Limpieza (D)**: dependencias muertas fuera (`aiosmtplib`, `aiohttp`, y `azure-core` explícita); Docker instala desde `uv.lock` (`uv sync --frozen`) y corre como usuario no-root con healthcheck; logging configurado al arranque (`LOG_LEVEL`) con contexto de lead/fase; `.idea/` fuera de git; `AGENTS.md` actualizado (CORS allowlist, comportamiento vigente); `README.md` creado (incluye la decisión de proyecto virtual sin `[build-system]`).
- **Calidad (E)**: suite pytest (contrato, pipeline con mocks, retries/alerta, rate limit, health), Ruff (lint+format) en `pyproject.toml` y CI de GitHub Actions (lint + tests en push/PR).
- **Email (F)**: saludo neutro profesional (sin usar el correo del destinatario como nombre), corrección de la coma extra y adjunto branded `Checklist-27-puntos-SALAZAR-Eng.pdf`.

## Capabilities

### New Capabilities

- `lead-api`: contrato HTTP del webhook (payload canónico `{email, need}`, 202, 422, 429) y CORS por allowlist desde `CORS_ORIGINS`.
- `notification-pipeline`: comportamiento del pipeline (validación del PDF, token de Google, retries/backoff, alerta de fallo definitivo, contenido del email, aislamiento de errores).
- `service-quality`: naming, health/readiness, higiene de settings/dependencias, Docker reproducible y no-root, logging, tests/Ruff/CI y documentación operativa.

### Modified Capabilities

- Ninguna: no existen specs previas en el repositorio (primer change del backend).

## Scope

Grupos A–F del brief: A contrato/API (H1, H8, H16, H18); B resiliencia (H3, H5, H12); C seguridad (H11, H6); D limpieza (H7, H10, H13, H14, H15, H19); E calidad (H4); F email (H9). H17 se documenta sin cambio de código.

## Non-goals

- Fix del frontend `necesidad` → `need` (repo externo; solo nota de coordinación).
- H2: dominio de producción de la landing y `CORS_ORIGINS` de producción (depende del dueño; ver Open Questions).
- Persistencia de leads en BD, panel de leads, idempotencia persistente.
- Captcha / anti-bot avanzado.
- i18n, plantillas de email configurables, multi-recurso (un solo `DRIVE_FILE_ID`).
- Despliegue real y workflow n8n (siguen como TODO futuro).
- Campos nuevos del contrato (nombre/empresa/teléfono).

## Open Questions

1. ¿Cuál será el dominio de producción de la landing para `CORS_ORIGINS`?
2. ¿Dónde/cómo se desplegará el backend (¿Render?) y con qué URL pública?
3. ¿Límite de rate limiting preferido para `/lead`? (propuesta: `5/minute`).
4. ¿`FROM_EMAIL` es un buzón monitoreado para usar como fallback de alertas, o se definirá `ALERT_EMAIL` explícito?

## Impact

- **Código**: `src/main.py`, `src/api/webhook.py`, `src/core/config.py`, `src/core/exceptions.py`, `src/services/drive_service.py`, `src/services/email_service.py`; nuevos `src/core/retry.py` y `src/core/logging.py`; `tests/**` y `conftest.py`.
- **API**: `/api/v1/lead` pasa a 202 y suma 429; `/api/v1/health` cambia `service` a `ms-notifier-webhook`; nuevo `/api/v1/health/ready`.
- **Dependencias**: +`slowapi`, +dev `pytest`, `pytest-asyncio`, `ruff`; −`aiosmtplib`, −`aiohttp`, −`azure-core` (permanece transitiva del SDK).
- **Configuración**: nuevas `ALERT_EMAIL`, `RATE_LIMIT_LEAD`, `MAX_PDF_SIZE_MB`, `LOG_LEVEL`; retiradas `AZURE_COMMUNICATION_ENDPOINT/_KEY`; `.env.example` actualizado.
- **Infra/entrega**: `Dockerfile`, `.github/workflows/ci.yml`, `.gitignore`, `.idea/` destrackeado, `README.md`, `AGENTS.md`.
- **Coordinación externa**: el frontend (`salazar-eng-landing`) debe enviar `need` (hoy envía `necesidad`) y setear `PUBLIC_LEAD_ENDPOINT`; sin ese cambio, la integración end-to-end responde 422.
