# Proposal: email-branded-template

## Why

El correo que recibe cada lead es hoy **texto plano genérico**: sin identidad visual, sin jerarquía, con un subject vago (`"Aquí tienes tu documento y el siguiente paso"`) y sin dejar claro que es un correo automático que no recibe respuestas (`src/services/email_service.py:12-38`). La landing y el PDF del checklist ya tienen un lenguaje de marca definido (navy `#0B2545`, accent `#1D4ED8`, Manrope + JetBrains Mono, microcopy mono tipo blueprint); el correo es el único punto de contacto que no lo refleja. La exploración del 2026-09-22 validó las capacidades técnicas (el SDK ACS soporta `html`; límites 10 MB / Gmail 102 KB) y el dueño ya tomó las decisiones de diseño; este change las convierte en un template branded con degradación elegante.

## What Changes

- **Correo multipart**: `build_lead_message` añade `content.html` y mantiene `plainText` completo y autosuficiente (mejora progresiva; la spec vigente exige texto plano funcional).
- **Identidad de marca en HTML**: banda navy `#0B2545`, cuerpo claro `#F8FAFC`/blanco, CTA accent `#1D4ED8` "bulletproof" (tabla, apto Outlook), hairlines `#CBD5E1`, firma `— SALAZAR Eng. · Software & Applied AI`; maquetación por tablas de 600px, **CSS inline, sin JavaScript, sin base64, sin fuentes embebidas**, HTML final **< 50 KB**.
- **Monograma por URL** con `alt="SALAZAR Eng."`, `width`/`height` explícitos y **wordmark textual de respaldo** siempre visible: el diseño se ve íntegro si el cliente bloquea la imagen. La URL es parametrizable (env var con default) para migrar de raw GitHub al dominio de marca sin tocar código.
- **Subject nuevo**: `Tu checklist: 27 puntos para modernizar tu sistema legacy`.
- **Nota de no-respuesta y footer**: `Este correo se envió automáticamente desde una dirección que no recibe respuestas.` + `BOOKING_URL` + WhatsApp (`https://wa.me/573145919465`, parametrizable).
- **Estrictamente no-respondible**: sin `replyTo` (decisión del dueño).
- **Texto plano actualizado** para reflejar subject, firma, nota de no-respuesta y WhatsApp.
- **Tests nuevos** (sin red): multipart, marcadores de marca, CTA, WhatsApp, `alt`, wordmark, nota, firma, ausencia de `replyTo`, presupuesto < 50 KB, y `plainText` autosuficiente.
- **Documentación**: `.env.example`, `README.md` y `AGENTS.md` con las nuevas variables.
- **Delta de spec**: `notification-pipeline` — MODIFIED del requirement "Contenido del email al lead".

## Capabilities

### New Capabilities

- Ninguna.

### Modified Capabilities

- `notification-pipeline`: el requirement "Contenido del email al lead" cambia (multipart HTML + identidad de marca + subject + nota de no-respuesta + firma + WhatsApp; sin `replyTo`).

## Scope

- `src/services/email_service.py`: helper de render HTML + `build_lead_message` multipart + `plainText` actualizado. `build_alert_message` **no se toca**.
- `src/core/config.py` + `.env.example`: `LEAD_EMAIL_LOGO_URL` y `LEAD_EMAIL_WHATSAPP_URL` (opcionales, con default).
- `tests/`: tests nuevos/actualizados del correo del lead.
- `README.md` y `AGENTS.md`: tabla de variables actualizada.
- Coordinación (fuera de este change): generar/publicar el `isotipo-white.png` real en el repo del frontend y verificar `HEAD 200`; aquí solo se define la URL objetivo y una task de verificación.

## Non-goals

- **CID inline y base64**: descartados por decisión del dueño (imagen hospedada por URL).
- **JavaScript**: imposible en clientes de correo (restricción del medio, no una elección).
- **Fuentes embebidas**: prohibidas por presupuesto (Gmail recorta > ~102 KB).
- **`jinja2` u otro motor de plantillas**: no se añade dependencia; el HTML se construye con un helper en Python.
- **Rediseño de la alerta interna** (`build_alert_message`): sin cambios.
- **`replyTo`**: no se usa.
- **Cambios en el repo del frontend** (asset, PDF, deploy): solo nota de coordinación por URL.
- **Cambios de infraestructura** (static files en el backend, CDN propio): futuros.

## Open Questions

1. ¿La URL final del monograma blanco será la de `public/` del frontend vía raw GitHub o el dominio de marca cuando exista? (El env var con default cubre la migración; el asset aún debe publicarse en el frontend — ver nota de coordinación.)
2. ¿Se mantiene WhatsApp como enlace del PDF (`wa.me/573145919465`) o cambiará el número? (Parametrizable por env var.)

## Impact

- **Código**: `src/services/email_service.py`, `src/core/config.py`.
- **Configuración**: nuevas `LEAD_EMAIL_LOGO_URL` y `LEAD_EMAIL_WHATSAPP_URL` (opcionales con default); `.env.example`, `README.md`, `AGENTS.md`.
- **Contrato externo**: el correo al lead pasa a multipart (mejora aditiva; `plainText` sigue existiendo); subject cambia.
- **Tests**: suite existente (38) debe seguir verde + tests nuevos del template.
- **Coordinación externa**: publicación del `isotipo-white.png` real en `salazar-eng-landing` (hoy da 404 en raw GitHub y el archivo existente es byte-idéntico al negro).
