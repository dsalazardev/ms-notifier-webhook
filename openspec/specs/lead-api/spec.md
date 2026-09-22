# lead-api Specification

## Purpose

Contrato HTTP público del webhook de captación de leads: payload canónico, códigos de respuesta, rate limiting por IP y CORS para la landing.

## Requirements

### Requirement: Contrato canónico del webhook de leads

El endpoint `POST /api/v1/lead` SHALL aceptar JSON con `email` (EmailStr) y `need` (str) como campos requeridos, y SHALL responder `202 Accepted` de inmediato con `{"status": "accepted", "message": "Lead recibido y procesando"}` mientras el procesamiento ocurre en background. El campo canónico es `need`; el backend SHALL NOT aceptar alias como `necesidad`.

#### Scenario: Payload válido aceptado

- **WHEN** se envía POST /api/v1/lead con email válido y `need` no vacío
- **THEN** responde 202 con `{"status": "accepted", ...}`
- **AND** el pipeline se agenda en background sin esperar su resultado

#### Scenario: Campo no canónico rechazado

- **WHEN** el payload trae `necesidad` en lugar de `need`
- **THEN** responde 422 y no se agenda el pipeline

#### Scenario: Email inválido rechazado

- **WHEN** el payload trae un email malformado
- **THEN** responde 422 y no se agenda el pipeline

#### Scenario: need ausente o vacío rechazado

- **WHEN** el payload omite `need` o lo envía vacío
- **THEN** responde 422 y no se agenda el pipeline

### Requirement: Rate limiting por IP en el webhook

El endpoint `/lead` SHALL limitar las solicitudes por IP según la variable `RATE_LIMIT_LEAD` (default `5/minute`), SHALL responder `429 Too Many Requests` con header `Retry-After` al excederse y SHALL NOT agendar el pipeline en esas solicitudes.

#### Scenario: Solicitudes dentro del límite

- **WHEN** un mismo origen realiza solicitudes dentro de la ventana y por debajo del límite
- **THEN** todas responden 202

#### Scenario: Límite excedido

- **WHEN** un origen supera el límite configurado dentro de la ventana
- **THEN** responde 429 con header `Retry-After`
- **AND** no se agenda el pipeline

#### Scenario: Límite configurable sin cambios de código

- **WHEN** se define `RATE_LIMIT_LEAD` con otro valor (por ejemplo `2/minute`)
- **THEN** el límite efectivo cambia sin modificar código

### Requirement: CORS por allowlist configurable

La aplicación SHALL permitir solicitudes cross-origin únicamente desde los orígenes listados en `CORS_ORIGINS`, SHALL responder al preflight de un origen permitido con `Access-Control-Allow-Origin` y SHALL rechazar (400, sin `Access-Control-Allow-Origin`) los orígenes no listados.

#### Scenario: Preflight desde origen permitido

- **WHEN** se envía OPTIONS /api/v1/lead con un `Origin` presente en `CORS_ORIGINS`
- **THEN** responde 200 con `Access-Control-Allow-Origin` igual al origen solicitado

#### Scenario: Preflight desde origen no listado

- **WHEN** se envía OPTIONS /api/v1/lead con un `Origin` ausente de `CORS_ORIGINS`
- **THEN** responde 400 sin `Access-Control-Allow-Origin`

#### Scenario: Alta de un origen de producción

- **WHEN** el dominio de la landing se agrega a `CORS_ORIGINS`
- **THEN** sus requests pasan a permitirse sin cambios de código
