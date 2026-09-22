# notification-pipeline Specification

## Purpose

Comportamiento del pipeline asíncrono que descarga el PDF del checklist desde Google Drive y lo envía por email: validación del documento, resiliencia, alertas de fallo y contenido del mensaje.

## Requirements

### Requirement: Validación del documento descargado

Antes de adjuntar, el pipeline SHALL validar el contenido descargado de Drive: SHALL exigir que comience con la firma `%PDF-` y SHALL rechazar archivos que excedan `MAX_PDF_SIZE_MB` (default 10 MB). Un documento inválido SHALL fallar de forma permanente y SHALL NOT enviar el email al lead.

#### Scenario: PDF válido

- **WHEN** Drive devuelve un PDF con firma `%PDF-` dentro del límite de tamaño
- **THEN** el pipeline adjunta el archivo y envía el email al lead

#### Scenario: Contenido que no es PDF

- **WHEN** el contenido descargado no comienza con `%PDF-` (por ejemplo un JSON o HTML de error de Drive)
- **THEN** el pipeline falla de forma permanente y no envía email al lead

#### Scenario: Archivo mayor al límite

- **WHEN** el tamaño del archivo excede `MAX_PDF_SIZE_MB` (según `Content-Length` o tamaño real)
- **THEN** el pipeline falla de forma permanente y no envía email al lead

### Requirement: Refresh condicional y no bloqueante del token de Google

El servicio de Drive SHALL refrescar el token de la service account solo cuando la credencial no sea válida, SHALL ejecutar el refresh fuera del event loop y SHALL evitar refrescos concurrentes duplicados.

#### Scenario: Credencial vigente

- **WHEN** la credencial ya es válida
- **THEN** no se invoca el refresh y la descarga usa el token vigente

#### Scenario: Credencial expirada

- **WHEN** la credencial expiró
- **THEN** se refresca una única vez y la descarga continúa con el token nuevo

#### Scenario: Refrescos concurrentes

- **WHEN** dos leads concurrentes requieren refresh al mismo tiempo
- **THEN** solo se ejecuta un refresh y el segundo espera su resultado

### Requirement: Reintentos con backoff para fallos transitorios

El pipeline SHALL reintentar operaciones de Drive y Azure ante errores transitorios (timeouts, fallos de red, 5xx, throttling) con backoff exponencial y un máximo de 3 intentos totales, y SHALL NOT reintentar errores permanentes (4xx de configuración o autorización y documentos inválidos).

#### Scenario: Fallo transitorio recuperado

- **WHEN** Drive o Azure falla transitoriamente y un intento posterior tiene éxito
- **THEN** el lead recibe su email y no se envía alerta

#### Scenario: Error permanente sin reintentos

- **WHEN** ocurre un error permanente (por ejemplo 404 del archivo de Drive o validación de documento)
- **THEN** no se realizan reintentos adicionales

#### Scenario: Reintentos agotados

- **WHEN** los 3 intentos fallan con errores transitorios
- **THEN** el pipeline se detiene y dispara la alerta al dueño

### Requirement: Alerta al dueño ante fallo definitivo

Cuando el pipeline falla definitivamente (reintentos agotados o error permanente), el sistema SHALL enviar un email de alerta a `ALERT_EMAIL` — o a `FROM_EMAIL` si `ALERT_EMAIL` no está definido — incluyendo el email del lead, la fase fallida y un resumen del error. Un fallo al enviar la alerta SHALL registrarse y SHALL NOT propagarse.

#### Scenario: Fallo definitivo dispara alerta

- **WHEN** el pipeline falla definitivamente
- **THEN** se envía una alerta a `ALERT_EMAIL` con lead, fase y error

#### Scenario: Fallback de alerta

- **WHEN** `ALERT_EMAIL` no está definido
- **THEN** la alerta se envía a `FROM_EMAIL`

#### Scenario: La alerta también falla

- **WHEN** el envío de la alerta falla
- **THEN** el error se registra y el pipeline termina sin propagar una nueva excepción

#### Scenario: Éxito sin alerta

- **WHEN** el pipeline completa con éxito
- **THEN** no se envía ninguna alerta

### Requirement: Contenido del email al lead

El email al lead SHALL usar un saludo neutro profesional sin la dirección del destinatario como nombre, SHALL interpolar `need` y `BOOKING_URL` en el cuerpo, y SHALL adjuntar `Checklist-27-puntos-SALAZAR-Eng.pdf` con content type `application/pdf`.

#### Scenario: Saludo neutro

- **WHEN** se construye el email
- **THEN** el saludo no contiene la dirección del destinatario ni puntuación duplicada

#### Scenario: Adjunto branded

- **WHEN** se construye el email
- **THEN** el adjunto se llama `Checklist-27-puntos-SALAZAR-Eng.pdf` y es `application/pdf`

#### Scenario: Contenido dinámico

- **WHEN** se construye el email
- **THEN** el cuerpo incluye el `need` del lead y el enlace `BOOKING_URL`

### Requirement: Aislamiento y trazabilidad del pipeline

El pipeline SHALL ejecutarse en background de modo que ningún fallo altere la respuesta `202` ya emitida ni exponga detalles internos al caller; los logs SHALL registrar el lead y la fase del fallo sin secretos.

#### Scenario: Fallo posterior a la respuesta

- **WHEN** el pipeline falla después de responder 202
- **THEN** el caller conserva su 202 y no recibe el error

#### Scenario: Logs con contexto

- **WHEN** una fase del pipeline falla
- **THEN** el log identifica el lead y la fase, sin secretos ni credenciales
