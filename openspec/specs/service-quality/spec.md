# service-quality Specification

## Purpose

Identidad unificada, salud operativa (liveness/readiness), higiene de configuración y dependencias, contenedor seguro y puertas de calidad automatizadas del servicio.

## Requirements

### Requirement: Identidad unificada del servicio

El nombre del servicio SHALL ser `ms-notifier-webhook` de forma consistente en el título de la aplicación FastAPI, en el campo `service` de `/health` y en el nombre del paquete.

#### Scenario: Health con identidad unificada

- **WHEN** se consulta GET /api/v1/health
- **THEN** responde `{"status": "ok", "service": "ms-notifier-webhook"}`

#### Scenario: Título de la aplicación

- **WHEN** se inspecciona el título de la app FastAPI
- **THEN** es `ms-notifier-webhook`

### Requirement: Liveness y readiness separados

El servicio SHALL exponer `/api/v1/health` como liveness sin verificar dependencias y `/api/v1/health/ready` como readiness de configuración (credenciales Google parseables, `DRIVE_FILE_ID`, connection string y `CORS_ORIGINS` presentes) sin llamadas a servicios externos; readiness SHALL responder 503 con el detalle de checks cuando la configuración crítica sea inválida.

#### Scenario: Configuración válida

- **WHEN** la configuración crítica está completa y parseable
- **THEN** GET /api/v1/health/ready responde 200 con estado ready y checks

#### Scenario: Configuración inválida

- **WHEN** `GOOGLE_CREDENTIALS_JSON` no es JSON parseable
- **THEN** readiness responde 503 not_ready sin llamar a Google

#### Scenario: Liveness independiente

- **WHEN** se consulta GET /api/v1/health
- **THEN** responde 200 sin comprobar dependencias externas

### Requirement: Configuración sin variables sin uso y tolerante a legacy

`Settings` SHALL exponer únicamente variables usadas por el código; `AZURE_COMMUNICATION_ENDPOINT` y `AZURE_COMMUNICATION_KEY` SHALL retirarse; las variables legacy presentes en el entorno SHALL ignorarse sin impedir el arranque; toda variable nueva SHALL documentarse en `.env.example`.

#### Scenario: Variables legacy presentes

- **WHEN** el entorno conserva las variables retiradas
- **THEN** la aplicación arranca normalmente

#### Scenario: Documentación de variables nuevas

- **WHEN** se revisa `.env.example`
- **THEN** incluye `ALERT_EMAIL`, `RATE_LIMIT_LEAD`, `MAX_PDF_SIZE_MB` y `LOG_LEVEL` con placeholders

#### Scenario: Sin variables muertas

- **WHEN** se comparan los campos de `Settings` con sus usos en el código
- **THEN** todos se usan

### Requirement: Dependencias reproducibles

`pyproject.toml` SHALL declarar solo dependencias usadas (directas o transitivas intencionales), `uv.lock` SHALL mantenerse consistente con `pyproject.toml`, y la imagen Docker SHALL instalar dependencias desde el lockfile en modo frozen.

#### Scenario: Lock consistente

- **WHEN** se ejecuta `uv lock --check`
- **THEN** termina sin errores

#### Scenario: Build reproducible

- **WHEN** se construye la imagen Docker
- **THEN** las versiones instaladas provienen de `uv.lock`

#### Scenario: Dependencias muertas retiradas

- **WHEN** se busca `aiosmtplib` y `aiohttp` en `pyproject.toml` e imports del código
- **THEN** no figuran como dependencias directas ni se importan

### Requirement: Contenedor seguro y operable

La imagen SHALL ejecutarse con un usuario no-root, SHALL exponer el puerto 8000 y SHALL declarar un HEALTHCHECK contra el endpoint de liveness.

#### Scenario: Proceso no-root

- **WHEN** el contenedor está en ejecución
- **THEN** el proceso de la aplicación no corre como root

#### Scenario: Healthcheck declarado

- **WHEN** se inspecciona la imagen
- **THEN** declara HEALTHCHECK y EXPOSE 8000

### Requirement: Logging configurado al arranque

La configuración de logging SHALL ocurrir al iniciar la aplicación (no como efecto secundario de importar un router) y SHALL respetar `LOG_LEVEL`; los logs del pipeline SHALL incluir lead y fase.

#### Scenario: Nivel configurable

- **WHEN** la aplicación arranca con `LOG_LEVEL=DEBUG`
- **THEN** el nivel efectivo de logging es DEBUG

#### Scenario: Contexto en logs de pipeline

- **WHEN** se procesa un lead
- **THEN** los logs permiten identificar lead y fase sin exponer secretos

### Requirement: Puertas de calidad automatizadas

El repositorio SHALL incluir una suite pytest sin llamadas reales a Drive/Azure que cubra contrato (payload válido y 422), pipeline (éxito, retry y alerta), rate limit (429) y health/readiness; SHALL incluir configuración de Ruff; y SHALL incluir un workflow de GitHub Actions que ejecute lint y tests en push y pull request.

#### Scenario: Tests sin red externa

- **WHEN** se ejecuta la suite de tests
- **THEN** pasa sin realizar llamadas reales a Google Drive ni a Azure

#### Scenario: Lint limpio

- **WHEN** se ejecuta `ruff check` y `ruff format --check`
- **THEN** terminan sin errores

#### Scenario: CI en push/PR

- **WHEN** ocurre un push o pull request
- **THEN** el workflow ejecuta lint y tests y falla si alguno no pasa

### Requirement: Documentación operativa vigente e higiene del repositorio

El repositorio SHALL incluir `README.md` con qué es el servicio, setup local, variables de entorno, comandos de tests y notas de despliegue, documentando la decisión de proyecto virtual sin `[build-system]`; `AGENTS.md` SHALL describir CORS como allowlist desde `CORS_ORIGINS` sin wildcard vigente; `.idea/` SHALL dejar de estar trackeado y SHALL figurar en `.gitignore`.

#### Scenario: README ejecutable

- **WHEN** se sigue el README en un entorno limpio
- **THEN** se puede instalar, correr la app y ejecutar los tests

#### Scenario: AGENTS.md vigente

- **WHEN** se revisa la sección CORS de `AGENTS.md`
- **THEN** describe la allowlist `CORS_ORIGINS` y no un wildcard vigente

#### Scenario: .idea fuera de git

- **WHEN** se ejecuta `git ls-files .idea`
- **THEN** no lista archivos
