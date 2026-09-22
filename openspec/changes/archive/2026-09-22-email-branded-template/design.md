# Design: email-branded-template

## Context

Ver `proposal.md` para la motivación. Estado y restricciones que moldean el enfoque:

- `build_lead_message` (`src/services/email_service.py:12-38`) construye un dict con `senderAddress`, `recipients`, `content.subject`, `content.plainText` y `attachments`; **no** usa `html`.
- El SDK ACS instalado soporta `content.html`, `replyTo`, `headers` y `attachments[].contentId` (`.venv/Lib/site-packages/azure/communication/email/_operations/_operations.py:160-207`).
- Límites: request total 10 MB (adjunto actual ~593 KB); Gmail recorta HTML > ~102 KB → presupuesto interno **< 50 KB**.
- Restricción del medio: sin JavaScript; Outlook usa el motor de Word; imágenes externas bloqueadas por defecto; SVG no soportado; base64 bloqueado en Outlook.
- Tokens de marca del sitio (`salazar-eng-landing/src/styles/global.css:3-13`): navy `#0B2545`, navy-700 `#16345E`, steel `#64748B`, surface `#F8FAFC`, line `#CBD5E1`, accent `#1D4ED8`, white `#FFFFFF`.
- Decisiones cerradas del dueño: imagen por URL (no CID/base64), alerta interna sin cambios, sin `replyTo`, footer con `BOOKING_URL` + WhatsApp, subject nuevo, asset blanco generado en el frontend (fuera de este change).

## Goals / Non-Goals

**Goals:**

- Correo multipart con HTML branded y `plainText` autosuficiente.
- Identidad de marca verificable en el HTML (banda navy, accent en CTA, firma, tipografías con fallback).
- Monograma por URL con `alt` + wordmark textual de respaldo; diseño íntegro sin imagen.
- Nota de no-respuesta visible en ambos cuerpos; sin `replyTo`.
- HTML < 50 KB, sin JS, sin base64, sin fuentes embebidas, tablas de 600px.
- Tests herméticos que fijen el contrato del template.

**Non-Goals (diseño):**

- No se introduce motor de plantillas ni dependencias nuevas.
- No se toca `build_alert_message` ni el pipeline de envío (`_send`).
- No se implementa CID/base64 ni static files del backend.
- No se hace i18n ni variantes por idioma.

## Decisions

### D1. HTML construido con helper Python (f-string), sin dependencias

`_render_lead_html(*, need, booking_url, whatsapp_url, logo_url) -> str` en `src/services/email_service.py`, con estilos inline y constantes de marca en el módulo.

- **Rationale**: una sola plantilla, sin I/O ni empaquetado extra, trivial de testear y con tamaño controlable.
- **Alternativas descartadas**: `jinja2` (dependencia nueva para una plantilla; además deja el HTML fuera del código o exige loader), archivo `.html` leído en runtime (I/O y riesgo de olvidar copiarlo en Docker), minificador externo (dependencia y pérdida de legibilidad).

### D2. URLs parametrizables por env var con default

- `LEAD_EMAIL_LOGO_URL: str = "https://raw.githubusercontent.com/dsalazardev/salazar-eng-landing/main/public/isotipo-white.png"` (URL objetivo; el asset aún debe publicarse en el frontend).
- `LEAD_EMAIL_WHATSAPP_URL: str = "https://wa.me/573145919465"`.
- Ambas opcionales en `Settings` (`src/core/config.py`), documentadas en `.env.example`, `README.md` y `AGENTS.md`.
- **Rationale**: migrar de raw GitHub al dominio de marca (o cambiar el número) no requiere tocar código ni re-desplegar la imagen.
- **Alternativas descartadas**: constantes en el módulo (migración = cambio de código), vars obligatorias (rompería despliegues existentes), hardcodear WhatsApp (mismo problema).

### D3. Degradación sin imagen: wordmark siempre visible

La banda navy muestra el monograma (`<img>` por URL, `alt="SALAZAR Eng."`, `width`/`height` explícitos) y, junto o debajo, el wordmark textual `SALAZAR Eng.` en blanco. El layout no depende de la imagen (celda de altura estable, sin `background-image`).

- **Rationale**: los clientes bloquean imágenes por defecto; el correo debe verse completo sin ellas.
- **Alternativa descartada**: solo `alt` (si la imagen se bloquea, la cabecera queda vacía y el correo pierde identidad).

### D4. Maquetación por tablas y botón "bulletproof"

`<table role="presentation" width="600">` con celdas y padding; CTA como celda con `bgcolor="#1D4ED8"` que contiene un `<a>` con padding y `color:#FFFFFF` (funciona en Outlook aunque ignore `border-radius`); sin `flex`/`grid`; CSS inline.

- **Rationale**: máxima compatibilidad (motor de Word de Outlook).
- **Alternativas descartadas**: botón con `border-radius` únicamente (Outlook lo cuadra; se acepta como degradación visual), VML condicional (complejidad innecesaria para un solo CTA).

### D5. Dark mode: superficies sólidas y contraste probado

Cuerpo claro (blanco/`#F8FAFC`) con texto navy; banda navy sólida con monograma blanco y wordmark blanco; sin `prefers-color-scheme` (soporte inconsistente). Se evita PNG transparente sobre fondos claros.

- **Rationale**: la inversión de colores en dark mode no puede controlarse de forma fiable; la combinación elegida mantiene contraste en ambos escenarios.
- **Alternativa descartada**: media queries de dark mode (soporte desigual y doble mantenimiento).

### D6. Presupuesto de tamaño verificado por test

Test que asserta `len(html.encode("utf-8")) < 50 * 1024`. Sin base64, sin fuentes, sin librerías JS; CSS inline (la repetición de estilos es el mayor contribuyente, se mantiene el marcado compacto).

- **Rationale**: el límite de Gmail (~102 KB) es real y silencioso (clipping); el test lo convierte en fallo temprano.
- **Alternativa descartada**: confiar en revisión manual.

### D7. `plainText` actualizado y autosuficiente

Nueva estructura: saludo neutro → need → mención del adjunto → CTA con `BOOKING_URL` → WhatsApp → firma → nota de no-respuesta. Sin HTML ni logo (imposibles en texto plano), pero con toda la información.

- **Rationale**: la spec exige que el texto plano funcione solo; es el fallback universal.

### D8. Alerta interna sin cambios

`build_alert_message` (`email_service.py:41-55`) queda intacto; sus tests actuales no se tocan.

### D9. Tests del template (herméticos)

Se añaden a `tests/test_services.py` (o módulo nuevo `tests/test_email_template.py`): multipart, subject, marcadores de marca (`#0B2545`, `#1D4ED8`), CTA con `BOOKING_URL`, WhatsApp, `alt`, wordmark, nota, firma, ausencia de `replyTo`, ausencia de `<script>`/`data:`/`@font-face`, tamaño < 50 KB, y `plainText` con la esencia. Sin red: `build_lead_message` es una función pura sobre `settings`.

- **Rationale**: el template es contrato de contenido; los tests lo fijan sin enviar correos.

### D10. Rollback

Revertir el commit del change restaura el correo de texto plano. Sin migración de datos. Si el asset no está publicado, el correo degrada (no rompe), y la URL puede re-apuntarse por env var sin revertir.

## Risks / Trade-offs

- [El asset blanco aún da 404 en la URL objetivo] → degradación por wordmark + task de verificación `HEAD` en el apply; pendiente documentado para el frontend.
- [Clientes bloquean imágenes] → wordmark + `alt` + dimensiones explícitas.
- [Outlook ignora `border-radius`] → CTA cuadrado con `bgcolor` (contraste garantizado); aceptado.
- [Dark mode agresivo en algún cliente] → superficies sólidas y contraste elegido; prueba manual futura.
- [HTML supera 50 KB al crecer el contenido] → test de presupuesto en CI; CSS inline compacto.
- [Subject nuevo y threading de Gmail] → correos de prueba con el mismo subject se agrupan; no afecta al lead.
- [Tests existentes asumen contenido] → el saludo neutro, adjunto y booking se preservan; si algún assert choca, se ajusta sin cambiar comportamiento.

## Migration Plan

1. Implementación en un commit (config + helper + mensaje + tests + docs).
2. Deploy: publicar el asset blanco en el frontend (coordinación), opcionalmente setear `LEAD_EMAIL_LOGO_URL`/`LEAD_EMAIL_WHATSAPP_URL` en el entorno; sin cambios de infraestructura.
3. Rollback: revertir el commit; la env var permite re-apuntar el logo sin tocar código.

## Open Questions

- ¿La URL final del monograma será raw GitHub o el dominio de marca? (El default + env var cubren la migración; no cambia specs ni tareas.)
- ¿El número de WhatsApp del PDF (`573145919465`) es el definitivo? (Parametrizable.)
- ¿Se querrá en el futuro una variante en inglés del correo? (i18n fuera de alcance.)
