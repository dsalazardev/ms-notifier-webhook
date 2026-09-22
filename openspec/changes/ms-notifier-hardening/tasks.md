# Tasks

## 1. Setup de dependencias y configuración de calidad

- [x] 1.1 Agregar `slowapi` a dependencias de runtime y `pytest`, `pytest-asyncio`, `ruff` al grupo dev de `pyproject.toml`; verificar con `uv sync` que la resolución e instalación terminan sin error.
- [x] 1.2 Configurar `[tool.ruff]` (target py314, line-length y reglas E/F/I/UP/B) y `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`, `testpaths = ["tests"]`) en `pyproject.toml`; verificar con `uv run ruff check .` sin errores y `uv run pytest --collect-only -q`.
- [x] 1.3 Regenerar `uv.lock` y verificar consistencia con `uv lock --check` (exit 0).

## 2. Grupo A — Contrato y API

- [x] 2.1 Fijar `status_code=202` en `@router.post("/lead")` y corregir el docstring; verificar inspeccionando `app.openapi()` (`responses` del POST incluye `202`) y con el test de contrato de 6.2.
- [x] 2.2 Unificar el naming a `ms-notifier-webhook` en el título de FastAPI (`src/main.py`) y en el campo `service` de `/health`; verificar con `python -c` sobre `app.title` y con el test de health de 6.2.
- [x] 2.3 Implementar `GET /api/v1/health/ready` con checks de configuración sin I/O (JSON de Google parseable, `DRIVE_FILE_ID`, connection string, `CORS_ORIGINS` no vacío, `MAX_PDF_SIZE_MB > 0`, `RATE_LIMIT_LEAD` parseable) devolviendo 200 `ready` o 503 `not_ready` con `checks`; verificar que no se llama a Google y con los tests de readiness de 6.2.
- [x] 2.4 Documentar la nota de coordinación del frontend externo (`necesidad`→`need`, `PUBLIC_LEAD_ENDPOINT`) en `README.md`; verificar que la nota existe y que no se modificó el repo del frontend.

## 3. Grupo B — Resiliencia del pipeline

- [x] 3.1 Crear `src/core/retry.py` con `run_with_retries` (attempts=3, backoff exponencial 0.5s→1.0s con jitter ±25%, `is_retryable`, `on_retry`); verificar con los tests unitarios de política de 6.3 (éxito al segundo intento, sin retry en permanente, agotamiento).
- [x] 3.2 Extender la taxonomía: atributo `retryable` en `NotificationServiceError` y nueva `DocumentValidationError`; clasificar Drive (timeout/redthrottling 429/5xx retryable; 401/403/404 no) y Azure (excepción del SDK retryable; `Failed` no); verificar con los tests de clasificación de 6.3.
- [x] 3.3 Drive: credenciales lazy (`_get_credentials`), refresh solo si `not creds.valid`, con `asyncio.Lock` y `asyncio.to_thread`; verificar con los tests de 6.5 (`valid=True` no refresca; concurrencia ejecuta un único refresh).
- [x] 3.4 Validar el documento descargado (firma `%PDF-` en primeros 1024 bytes y tamaño ≤ `MAX_PDF_SIZE_MB`, por `Content-Length` y tamaño real); verificar con los tests de 6.5 (PDF válido, no-PDF y oversize → fallo permanente sin email).
- [x] 3.5 Integrar retries por fase en `process_lead_pipeline` (descarga y envío por separado, log de intento/fase) con alerta única al agotar o ante error permanente; verificar con los tests de 6.3 (transitorio→éxito sin alerta, permanente sin retry, agotado→alerta).
- [x] 3.6 Implementar `AsyncEmailService.send_alert_email` (fallback `ALERT_EMAIL`→`FROM_EMAIL`, sin adjunto y sin propagar el fallo de la alerta); verificar con los tests de 6.3 (fallback y fallo de alerta solo loguea).

## 4. Grupo C — Seguridad

- [x] 4.1 Limpiar `Settings`: retirar `AZURE_COMMUNICATION_ENDPOINT`/`AZURE_COMMUNICATION_KEY`, agregar `ALERT_EMAIL`, `RATE_LIMIT_LEAD`, `MAX_PDF_SIZE_MB`, `LOG_LEVEL` y fijar `extra="ignore"`; verificar con el test de 6.2 (app arranca con variables retiradas presentes) y con `.env.example` actualizado (nuevas documentadas, retiradas como legado).
- [x] 4.2 Añadir rate limiting con `slowapi` a `/lead` (key por IP, límite leído en runtime) con handler de `429` y header `Retry-After`; verificar con el test de 6.4 (exceder límite responde 429 y no agenda pipeline).
- [x] 4.3 Eximir `/health` y `/health/ready` del límite y comprobar que el límite es configurable (`RATE_LIMIT_LEAD=2/minute` cambia el comportamiento); verificar con los tests de 6.4.
- [x] 4.4 Documentar el caveat de IP tras proxy (`--proxy-headers`/`FORWARDED_ALLOW_IPS`) en `README.md` y `AGENTS.md`; verificar que la nota existe.

## 5. Grupo D — Limpieza y mantenibilidad

- [x] 5.1 Retirar `aiosmtplib`, `aiohttp` y `azure-core` de `pyproject.toml`; verificar con búsqueda en `src/` que no hay imports y con `uv lock --check` (exit 0).
- [x] 5.2 Dockerfile reproducible y seguro: `uv sync --frozen --no-dev` con PATH al venv, usuario no-root `appuser` y `HEALTHCHECK` contra liveness; verificar con `docker build` y `docker run` (proceso no-root, healthcheck healthy) si Docker está disponible; si no, dejar constancia en el reporte.
- [x] 5.3 Crear `src/core/logging.py` con `configure_logging()` (lee `LOG_LEVEL`, formato con timestamp/nivel/logger/mensaje) y llamarlo en `src/main.py`; eliminar `basicConfig` de `src/api/webhook.py`; verificar con el test de `LOG_LEVEL=DEBUG` de 6.2.
- [x] 5.4 Añadir contexto (lead y fase) a los logs del pipeline sin secretos; verificar con el test de caplog de 6.3.
- [x] 5.5 Sacar `.idea/` de git (`git rm -r --cached .idea`) y agregar `.idea/` a `.gitignore`; verificar con `git ls-files .idea` sin resultados.
- [x] 5.6 Actualizar `AGENTS.md`: CORS como allowlist `CORS_ORIGINS` (sin wildcard), naming `ms-notifier-webhook`, endpoints (202 y readiness), variables nuevas, comandos de calidad y nota H17 (`from_connection_string` síncrono sin I/O); verificar que no queda `"*"` ni `localhost:4321` hardcodeado como CORS vigente.
- [x] 5.7 Crear `README.md` (qué es, requisitos Python 3.14/uv, setup, variables de entorno, comandos de run/tests/lint, Docker y notas de despliegue, decisión de proyecto virtual sin `[build-system]`); verificar siguiendo el README en el entorno actual.

## 6. Grupo E — Calidad (tests, lint, CI)

- [x] 6.1 Crear `conftest.py` que define variables de entorno dummy (sin secretos reales) antes de importar `src`, con fixtures de cliente ASGI y reset del limiter; verificar que `uv run pytest -q` colecta sin errores de import.
- [x] 6.2 Tests de contrato/API: payload válido 202; `necesidad` 422; email inválido 422; `need` ausente 422; health (naming) y readiness (200/503, sin llamar a Google); variables legacy presentes y `LOG_LEVEL=DEBUG`; verificar `uv run pytest` verde.
- [x] 6.3 Tests de pipeline con mocks (cero red): éxito, transitorio con retry, permanente sin retry, agotado con alerta, fallo de alerta, logs con lead/fase; verificar `uv run pytest` verde.
- [x] 6.4 Tests de rate limit (429 + `Retry-After`, exención de health) y CORS preflight (permitido 200/ACAO, no listado 400); verificar `uv run pytest` verde.
- [x] 6.5 Tests de servicios: validación PDF (firma/tamaño), refresh condicional y concurrente del token, contenido del email (saludo neutro, sin coma extra, adjunto branded); verificar `uv run pytest` verde.
- [x] 6.6 Formatear con `uv run ruff format .` y corregir con `uv run ruff check --fix .`; verificar `uv run ruff check .` y `uv run ruff format --check .` limpios.
- [x] 6.7 Crear `.github/workflows/ci.yml` (push/PR a `main`: setup-uv + Python 3.14, `uv sync --frozen`, `ruff check`, `ruff format --check`, `pytest -q`); verificar la sintaxis del YAML y el primer run en GitHub tras push (`actionlint` si está disponible).

## 7. Grupo F — Contenido del email

- [x] 7.1 Cambiar el saludo a neutro profesional (sin el correo del destinatario como nombre), eliminar la coma extra y renombrar el adjunto a `Checklist-27-puntos-SALAZAR-Eng.pdf`; verificar con los tests de 6.5.

## 8. Verificación final (criterios de aceptación del change)

- [x] 8.1 Verificar `uv lock --check` (exit 0) y `uv run python -c "from src.main import app"` sin error.
- [x] 8.2 Verificar `uv run ruff check .`, `uv run ruff format --check .` limpios y `uv run pytest -q` verde sin acceso a red externa.
- [x] 8.3 Verificar imagen Docker (si disponible): proceso no-root, healthcheck healthy y `GET /api/v1/health/ready` con 200 en configuración válida.
- [x] 8.4 Repasar los 10 criterios de aceptación del brief contra specs y tests; registrar desviaciones en el reporte del apply.
