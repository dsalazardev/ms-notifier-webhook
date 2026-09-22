# Spec Delta

## MODIFIED Requirements

### Requirement: Contenido del email al lead

El email al lead SHALL ser multipart (`html` + `plainText`) con identidad de marca SALAZAR Eng. (banda navy, CTA accent, firma y tipografías con fallback); SHALL usar el subject `Tu checklist: 27 puntos para modernizar tu sistema legacy`, mostrar el monograma por URL con `alt` y respaldo textual, incluir la nota de no-respuesta y el footer con `BOOKING_URL` y WhatsApp; SHALL NOT incluir `replyTo`, JavaScript, base64 ni fuentes embebidas; el HTML SHALL pesar menos de 50 KB.

#### Scenario: Saludo neutro

- **WHEN** se construye el email
- **THEN** el saludo no contiene la dirección del destinatario ni puntuación duplicada

#### Scenario: Adjunto branded

- **WHEN** se construye el email
- **THEN** el adjunto se llama `Checklist-27-puntos-SALAZAR-Eng.pdf` y es `application/pdf`

#### Scenario: Contenido dinámico

- **WHEN** se construye el email
- **THEN** el cuerpo incluye el `need` del lead y el enlace `BOOKING_URL`

#### Scenario: Correo multipart

- **WHEN** se construye el mensaje
- **THEN** el `content` incluye `html` y `plainText`
- **AND** ambos contienen la información esencial (need, mención del adjunto, enlace de agendamiento, nota de no-respuesta y firma)

#### Scenario: Identidad de marca y presupuesto técnico

- **WHEN** se renderiza el HTML
- **THEN** usa banda navy `#0B2545`, accent `#1D4ED8` en el CTA, maquetación por tablas de 600px y CSS inline
- **AND** no contiene JavaScript, `data:` URIs ni fuentes embebidas
- **AND** pesa menos de 50 KB

#### Scenario: Monograma hospedado con degradación sin imagen

- **WHEN** el HTML se renderiza
- **THEN** el monograma se referencia por URL con `alt` descriptivo y dimensiones explícitas
- **AND** un wordmark textual de respaldo mantiene la cabecera legible si la imagen se bloquea

#### Scenario: No-respondible

- **WHEN** se construye el mensaje
- **THEN** no incluye `replyTo`
- **AND** el footer muestra la nota de que es un correo automático que no recibe respuestas

#### Scenario: Subject y footer actualizados

- **WHEN** se construye el mensaje
- **THEN** el subject es `Tu checklist: 27 puntos para modernizar tu sistema legacy`
- **AND** el footer incluye `BOOKING_URL` y el enlace de WhatsApp

#### Scenario: Texto plano autosuficiente

- **WHEN** se lee solo el `plainText`
- **THEN** contiene el need, la mención del adjunto, el enlace de agendamiento, el WhatsApp, la firma y la nota de no-respuesta
