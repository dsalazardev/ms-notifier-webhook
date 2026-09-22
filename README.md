# ms-notifier-webhook

Microservicio backend del lead magnet de SALAZAR Eng.: recibe los leads del formulario de la landing (`POST /api/v1/lead`), descarga el PDF del checklist desde Google Drive y lo envía por email (Azure Communication Services) con un enlace de agendamiento.

## Requisitos

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- Docker (opcional, para construir la imagen)

## Setup local

```bash
cp .env.example .env   # completar credenciales reales
uv sync
uv run uvicorn src.main:app --reload
```

## Variables de entorno

| Variable | Descripción | Requerida |
|---|---|---|
| `GOOGLE_CREDENTIALS_JSON` | JSON de la service account de Google (Drive readonly) | Sí |
| `DRIVE_FILE_ID` | ID del PDF en Google Drive | Sí |
| `AZURE_EMAIL_CONNECTION_STRING` | Connection string de Azure Communication Services Email | Sí |
| `FROM_EMAIL` | Remitente verificado en ACS | Sí |
| `BOOKING_URL` | Enlace de agendamiento incluido en el email | Sí |
| `CORS_ORIGINS` | Allowlist JSON de orígenes permitidos (p. ej. `["http://localhost:4321"]`) | Sí |
| `ALERT_EMAIL` | Destinatario de alertas por fallo definitivo del pipeline (default: `FROM_EMAIL`) | No |
| `RATE_LIMIT_LEAD` | Límite por IP de `/lead` en formato limits (default: `5/minute`) | No |
| `MAX_PDF_SIZE_MB` | Tamaño máximo del PDF adjuntado en MB (default: `10`) | No |
| `LOG_LEVEL` | Nivel de logging (default: `INFO`) | No |

Las variables legacy `AZURE_COMMUNICATION_ENDPOINT` y `AZURE_COMMUNICATION_KEY` ya no se usan: si siguen presentes en el `.env`, se ignoran sin efecto.

## Endpoints

- `GET /api/v1/health` — liveness (`{"status":"ok","service":"ms-notifier-webhook"}`).
- `GET /api/v1/health/ready` — readiness de configuración (200 `ready` / 503 `not_ready`), sin llamadas externas.
- `POST /api/v1/lead` — recibe `{"email": "...", "need": "..."}`, responde `202 Accepted` y procesa en background.

El pipeline reintenta fallos transitorios de Drive/Azure (3 intentos, backoff exponencial) y envía una alerta a `ALERT_EMAIL` si falla de forma definitiva.

### Rate limiting

`/lead` está limitado por IP según `RATE_LIMIT_LEAD` (default `5/minute`) y responde `429` con `Retry-After` al excederse. El store es en memoria: con más de una instancia se necesita un backend compartido (p. ej. Redis).

Detrás de un proxy (Render u otro), configurar `--proxy-headers`/`FORWARDED_ALLOW_IPS` para que el límite use la IP real del cliente y no la del proxy.

### CORS

El backend solo acepta orígenes listados en `CORS_ORIGINS`. En producción se debe agregar el dominio de la landing; en desarrollo el default incluye `http://localhost:4321` (puerto de Astro).

## Comandos

```bash
uv run uvicorn src.main:app --reload   # desarrollo
uv run pytest -q                       # tests (herméticos, sin red)
uv run ruff check .                    # lint
uv run ruff format .                   # formato
uv run ruff format --check .           # verificación de formato
```

## Docker

```bash
docker build -t ms-notifier-webhook .
docker run --env-file .env -p 8000:8000 ms-notifier-webhook
```

La imagen instala dependencias desde `uv.lock` (`uv sync --frozen`), corre como usuario no-root (`appuser`) y declara un `HEALTHCHECK` contra `/api/v1/health`.

## Tests y CI

La suite de pytest usa variables dummy y mocks: no llama a Google Drive ni a Azure. El workflow `.github/workflows/ci.yml` ejecuta lint, verificación de formato y tests en push y pull request.

## Notas de despliegue

- Configurar en el entorno de deploy: `ALERT_EMAIL`, `RATE_LIMIT_LEAD`, `MAX_PDF_SIZE_MB` y `LOG_LEVEL` (las retiradas pueden quedarse).
- Agregar el dominio de producción de la landing a `CORS_ORIGINS`.
- El proyecto es **virtual** (no tiene `[build-system]`): `uv.lock` lo marca como `source = { virtual = "." }`. Es intencional: es una aplicación, no una librería distribuible; `uv sync` instala solo dependencias.

## Coordinación con el frontend

El contrato canónico del webhook es `{"email": ..., "need": ...}`. La landing (`salazar-eng-landing`, repo externo) debe:

- enviar el campo `need` (hoy envía `necesidad`) y
- configurar `PUBLIC_LEAD_ENDPOINT` apuntando a `POST /api/v1/lead`.

Sin esos cambios, la integración end-to-end responde `422`.
