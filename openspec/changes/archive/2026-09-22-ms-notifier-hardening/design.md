# Design: ms-notifier-hardening

## Context

Ver `proposal.md` para la motivación. Estado y restricciones que moldean el enfoque:

- Monolito FastAPI de 3 capas (`api/`, `core/`, `models/`, `services/`); `settings`, `drive_service` y `email_service` se instancian **a nivel de import** (`src/api/webhook.py:13-14`, `src/core/config.py:27`), y Uvicorn corre con **1 worker** (`Dockerfile:18`).
- El pipeline usa `BackgroundTasks` in-process (`src/api/webhook.py:44`): sin cola, sin persistencia, sin reintentos (`src/api/webhook.py:30-35`).
- `_get_access_token()` refresca el token de Google de forma síncrona en **cada** request (`src/services/drive_service.py:15-21`).
- Docker instala con `uv pip install --system -r pyproject.toml` e **ignora** `uv.lock` (`Dockerfile:12`).
- No existen specs previas, tests, linter ni CI; es el primer change OpenSpec del backend.
- Restricciones fijas: Python 3.14 + uv, contrato canónico `need` (sin alias), un solo `DRIVE_FILE_ID`, sin persistencia, sin tocar el frontend.

## Goals / Non-Goals

**Goals:**

- Pipeline resiliente: reintentos con backoff para fallos transitorios y alerta al dueño ante fallo definitivo (H3).
- Protección anti-abuso del endpoint público con rate limiting configurable (H11).
- No bloquear el event loop con el refresh del token y refrescar solo cuando haga falta (H5).
- Validar tipo/tamaño del documento antes de adjuntarlo (H12).
- Contrato, naming y salud operativa explícitos (H1, H8, H16, H18).
- Higiene: settings sin variables muertas (H6), dependencias reproducibles (H7, H10), logging correcto (H13), documentación y repo limpios (H14, H15, H19).
- Puertas de calidad automatizadas: pytest, Ruff y CI (H4).

**Non-Goals (diseño):**

- No se introduce contenedor de DI, cola de trabajos, Redis ni `create_app()`: el blast radius debe ser mínimo y testeable con monkeypatch (ver D11).
- No se persisten leads (fuera de alcance; próxima iteración).
- No hay canal de alerta secundario si Azure está caído (solo log crítico).
- No se unifica logging estructurado JSON ni métricas: `LOG_LEVEL` + mensajes con contexto.

## Decisions

### D1. Reintentos con backoff en el orquestador, no en los servicios

Nuevo helper `src/core/retry.py`:

```
async def run_with_retries(operation, *, attempts=3, base_delay=0.5, factor=2.0,
                           jitter=0.25, is_retryable, on_retry=None)
```

- `attempts=3` (2 reintentos): delays ~0.5s y ~1.0s con jitter ±25% ⇒ <2.5s de espera máxima.
- `process_lead_pipeline` envuelve la descarga y el envío por separado, de modo que el reintento de email no vuelve a descargar el PDF.
- **Rationale**: el orquestador conoce la fase, puede loguear el intento y dispara la alerta una sola vez al final; los servicios permanecen puros.
- **N1 (decisión de implementación)**: el timeout por intento de la descarga de Drive se reduce a `15.0s` (`DRIVE_REQUEST_TIMEOUT_SECONDS`), de modo que 3 intentos + backoff no acumulen ~90s con el timeout anterior de 30s (peor caso ≈ 47s).
- **Alternativas**: decorador en los servicios (oculta fase/alertas); `tenacity` (dependencia extra para una función de 20 líneas).

### D2. Taxonomía de errores explícita y retryable

- `NotificationServiceError` gana `retryable: bool = False` (atributo de clase).
- `DriveDownloadError` / `EmailDeliveryError` aceptan `retryable` por instancia.
- Nueva `DocumentValidationError(NotificationServiceError)` (siempre permanente).
- Clasificación Drive: reintentar `httpx.TimeoutException`, `httpx.TransportError` y status 429/5xx; **no** 401/403/404 ni validación.
- Clasificación Azure: reintentar cuando el SDK **lanza** excepción (red/infra); `result["status"] == "Failed"` se trata como permanente (contenido/destinatario).
- **Rationale**: política determinista, testeable sin enumerar códigos ACS frágiles.

### D3. Rate limiting con `slowapi` (key por IP, límite en runtime)

- `Limiter(key_func=get_remote_address)`; el límite se lee en tiempo de request vía callable que devuelve `settings.RATE_LIMIT_LEAD` (default `5/minute`), de modo que los tests lo cambian con monkeypatch.
- Handler de `RateLimitExceeded` → `429` con `Retry-After`; exento `/health` y `/health/ready`.
- Store en memoria: suficiente con 1 worker; multi-instancia exigiría Redis (non-goal, documentado).
- **Riesgo de proxy**: `get_remote_address` usa `request.client.host`; detrás de Render debe correr con `--proxy-headers` y `FORWARDED_ALLOW_IPS` correctos; si no, se agrupa por IP del proxy (documentado en README/AGENTS y Open Questions).
- **Alternativas**: middleware propio con dict (reinventa `Retry-After`, reset y parseo de límites); límite global (no protege por origen).

### D4. Alerta al dueño reutilizando el cliente Azure

- `ALERT_EMAIL: EmailStr | None = None`; si es `None`, se envía a `FROM_EMAIL`.
- Nuevo `AsyncEmailService.send_alert_email(lead_email, phase, error_summary)`: mismo cliente, asunto fijo, sin adjunto, **sin** retries propios (para no alargar el background task); si falla → `logger.critical`, nunca propaga.
- Se invoca una sola vez, después de agotar retries o ante error permanente.
- **Limitación aceptada**: si Azure está caído, la alerta también falla y solo queda el log.

### D5. Validación del PDF por firma y tamaño

- Firma: buscar `%PDF-` dentro de los primeros 1024 bytes (tolera bytes previos permitidos por el spec PDF).
- Tamaño: pre-check de `Content-Length` cuando exista + post-check de `len(content)`; límite `MAX_PDF_SIZE_MB: int = 10`.
- No se valida `Content-Type` (Drive puede responder `application/octet-stream` aun para PDFs).
- Falla con `DocumentValidationError` (permanente, sin retry).
- **Alternativa descartada**: parsear con `pypdf` (dependencia y CPU innecesarias para nuestro propio archivo controlado).

### D6. Token de Google: lazy, condicional, con lock y fuera del event loop

- Credenciales **lazy**: `AsyncDriveService.__init__` deja de llamar `from_service_account_info`; `_get_credentials()` las construye en el primer uso. Beneficio: la app importa y el readiness responde aunque el JSON tenga problemas; los tests no necesitan una key real.
- Refresh:
  ```
  if not creds.valid:
      async with self._lock:
          if not creds.valid:
              await asyncio.to_thread(creds.refresh, Request())
  token = creds.token
  ```
- `asyncio.Lock` creado en `__init__` (sin acoplamiento a loop en Python ≥3.10).
- **Rationale**: elimina el bloqueo del event loop y el refresh redundante por request; el doble check evita tormentas de refresh concurrentes.

### D7. Settings: sin variables muertas y tolerantes a legacy

- Retirar `AZURE_COMMUNICATION_ENDPOINT` y `AZURE_COMMUNICATION_KEY`.
- Agregar `ALERT_EMAIL: EmailStr | None = None`, `RATE_LIMIT_LEAD: str = "5/minute"`, `MAX_PDF_SIZE_MB: int = 10`, `LOG_LEVEL: str = "INFO"`.
- Fijar `SettingsConfigDict(extra="ignore", env_file=".env", env_file_encoding="utf-8")` **explícitamente**: garantiza el escenario “vars retiradas siguen en `.env` y la app arranca” (el default de pydantic-settings no debe asumirse).
- `.env.example`: eliminar las retiradas con nota de legado y documentar las nuevas.

### D8. Docker reproducible y no-root

- `COPY pyproject.toml uv.lock ./` y `RUN uv sync --frozen --no-dev` (proyecto virtual ⇒ instala solo dependencias en `/app/.venv`); `ENV PATH="/app/.venv/bin:$PATH"`.
- Usuario no-root `appuser` (UID 1000) con `useradd`, ownership de `/app`.
- `HEALTHCHECK` con `python -c "urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')"` (slim no trae `curl`).
- Se mantiene `--workers 1` (coherente con el rate limit en memoria).
- **Alternativas**: `uv pip install --system` (ignora lock, es el problema actual); multi-stage (complejidad sin beneficio para una app de 12 archivos).

### D9. Logging configurado en el arranque

- Nuevo `src/core/logging.py::configure_logging()`: `basicConfig` idempotente con formato `timestamp | level | logger | message`, nivel desde `settings.LOG_LEVEL`.
- `src/main.py` la llama a nivel de módulo antes de crear la app; se elimina `logging.basicConfig` de `src/api/webhook.py:11`.
- Mensajes del pipeline con lead y fase (`drive.download`, `email.send`, `alert.send`).

### D10. Naming, 202 explícito y readiness

- Título FastAPI y `service` de `/health` → `ms-notifier-webhook` (**BREAKING** menor del payload de health).
- `@router.post("/lead", status_code=202)` y docstring corregido.
- Nuevo `GET /api/v1/health/ready` en `src/api/webhook.py`: verifica **configuración** (`google_creds_dict` parseable, `DRIVE_FILE_ID`, connection string, `CORS_ORIGINS` no vacío, `MAX_PDF_SIZE_MB > 0`, `RATE_LIMIT_LEAD` parseable por `limits`) **sin** I/O externo; responde `{"status":"ready","checks":{...}}` (200) o `{"status":"not_ready","checks":{...}}` (503).

### D11. Estrategia de tests sin red y sin refactor de DI

- `conftest.py` define variables de entorno dummy **antes** de importar `src` (servicio-account JSON con forma válida pero sin key real; `RATE_LIMIT_LEAD="1000/minute"` para no interferir).
- La app se importa normalmente (`from src.main import app`); los tests HTTP usan `httpx.AsyncClient(transport=ASGITransport(app=app))` o `TestClient`.
- Servicios mockeados con `AsyncMock` sobre los objetos de módulo (`src.api.webhook.drive_service`, `email_service`) — gracias a D6 no se necesita key real para importar.
- Test de rate limit en módulo dedicado: monkeypatch del límite + `limiter.reset()` en fixture autouse; se evita el orden de tests frágil.
- Test de refresh condicional con credenciales fake (`valid=True/False`) contando llamadas a `refresh`.
- **Alternativa descartada**: `create_app()` + inyección de dependencias (mejor testabilidad, pero reestructura arranque y servicios en un change ya grande; se puede hacer luego si crece la suite).

### D12. CI en GitHub Actions

- `.github/workflows/ci.yml`: en `push`/`pull_request` a `main`; `astral-sh/setup-uv` con Python 3.14 (cache de uv); `uv sync --frozen`; `uv run ruff check .`; `uv run ruff format --check .`; `uv run pytest -q`.
- Sin servicios externos ni secretos: la suite es hermética.

### D13. Higiene de repositorio

- `git rm -r --cached .idea` y `.idea/` en `.gitignore` (mantener la exclusión existente de `.idea/workspace.xml`); no se borran los archivos locales del IDE.
- `README.md` documenta la decisión de proyecto virtual sin `[build-system]` (uv.lock lo marca `source = { virtual = "." }`).
- `AGENTS.md`: reescribir la sección de CORS (allowlist `CORS_ORIGINS`, sin wildcard) y actualizar naming, endpoints, variables nuevas y comandos de calidad.

### D14. `from_connection_string` síncrono (H17): se documenta, no se mueve

No hace I/O de red (solo parsea la cadena); moverlo a `__init__` empeoraría el fallo temprano en import. Se deja como está y se documenta en `AGENTS.md`/design.

## Risks / Trade-offs

- [Rate limit en memoria no funciona entre instancias] → 1 worker y una instancia hoy; si Render escala, migrar a Redis; documentado en README.
- [IP real detrás de proxy] → correr uvicorn con `--proxy-headers`/`FORWARDED_ALLOW_IPS`; documentar y verificar en el deploy (Open Question).
- [Azure caído ⇒ la alerta también falla] → log `critical`; canal secundario fuera de alcance.
- [**BREAKING** del campo `service` en `/health`] → único consumidor conocido: ping de Render (comentario `src/api/webhook.py:50`); coordinar si aparece otro.
- [**BREAKING** de 200→202 en `/lead`] → el frontend solo mira `response.ok` (2xx), sin impacto; documentar para posibles consumidores.
- [Quitar `azure-core` explícita] → sigue transitiva de `azure-communication-email`; si el código importa `azure.core` en el futuro, re-declararla.
- [`uv sync --frozen` falla si `uv.lock` está desincronizado] → regenerar lock en el grupo de setup y verificar en CI.
- [Firma `%PDF-` puede rechazar PDFs con basura previa >1 KB] → el archivo es nuestro y controlado; límite documentado.
- [`5/minute` puede afectar redes NAT compartidas] → configurable por env; default revisable por el dueño (Open Question).
- [Validación de límite de rate en readiness] → si `limits` no parsea el string, readiness 503 (config rota).

## Migration Plan

1. **Orden de implementación**: setup (deps/config) → A contrato → B resiliencia → C seguridad → D limpieza → E calidad → F email → verificación. Un commit convencional por grupo; `uv.lock` regenerado en setup.
2. **Deploy**: actualizar entorno con `ALERT_EMAIL`, `RATE_LIMIT_LEAD`, `MAX_PDF_SIZE_MB`, `LOG_LEVEL` (las retiradas pueden quedarse); reconstruir la imagen; verificar `/api/v1/health/ready` y un lead de prueba E2E con el frontend alineado.
3. **Rollback**: revertir el commit del grupo afectado (los cambios funcionales están agrupados); alternativas sin código: `RATE_LIMIT_LEAD` alto desactiva de facto el límite y `MAX_PDF_SIZE_MB` alto relaja la validación. Las alertas solo se desactivan revirtiendo el grupo B (no hay toggle para no dejar alertas huérfanas silenciosas). La imagen se revierte por tag anterior en el proveedor.

## Open Questions

- ¿El entorno de despliegue configura `--proxy-headers`/`FORWARDED_ALLOW_IPS` para que el rate limit vea la IP real? (depende del proveedor; no cambia el diseño).
- Preguntas de negocio del `proposal.md` (dominio de producción, plataforma, límite preferido, `ALERT_EMAIL`): se responden en deploy, no cambian specs ni tareas.
