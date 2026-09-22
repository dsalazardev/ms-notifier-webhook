# Tasks

## 1. Configuración y documentación

- [x] 1.1 Añadir `LEAD_EMAIL_LOGO_URL` y `LEAD_EMAIL_WHATSAPP_URL` a `Settings` (`src/core/config.py`) como opcionales con default (raw GitHub del isotipo blanco y `https://wa.me/573145919465`) y a `.env.example`; verificar con `uv run python -c` que `settings` expone ambos valores por defecto y que `src.main` importa sin error.
- [x] 1.2 Documentar ambas variables en las tablas de entorno de `README.md` y `AGENTS.md`; verificar por búsqueda que aparecen en ambos archivos.

## 2. Implementación del template

- [x] 2.1 Crear `_render_lead_html(...)` en `src/services/email_service.py` (banda navy con monograma por URL con `alt` y dimensiones + wordmark textual, título, `need`, mención del adjunto, CTA bulletproof accent, firma, nota de no-respuesta); verificar con `uv run python -c` que el HTML contiene los marcadores de marca y mide menos de 50 KB.
- [x] 2.2 Añadir `html` a `build_lead_message`, aplicar el subject `Tu checklist: 27 puntos para modernizar tu sistema legacy` y actualizar el `plainText` (nota de no-respuesta, firma y WhatsApp); no añadir `replyTo`; verificar con los tests de 3.1 y 3.2.
- [x] 2.3 Confirmar la degradación sin imagen (wordmark visible y layout independiente del `<img>`); verificar con el test de wordmark de 3.1 y revisión del HTML generado.

## 3. Tests

- [x] 3.1 Tests del HTML del lead: multipart (`html` + `plainText`), subject nuevo, marcadores `#0B2545`/`#1D4ED8`, CTA con `BOOKING_URL`, WhatsApp, `alt` y wordmark, nota de no-respuesta, firma, ausencia de `replyTo`, ausencia de `<script>`/`data:`/`@font-face` y tamaño < 50 KB; verificar `uv run pytest` verde.
- [x] 3.2 Test del `plainText` autosuficiente (need, mención del adjunto, `BOOKING_URL`, WhatsApp, firma y nota); verificar `uv run pytest` verde.
- [x] 3.3 Ejecutar la suite completa (38 existentes + nuevos) y `uv run ruff check .` + `uv run ruff format --check .`; verificar todo limpio.

## 4. Verificación del asset (coordinación con el frontend)

- [x] 4.1 Ejecutar `HEAD` contra `LEAD_EMAIL_LOGO_URL` (con control de `isotipo-se.png`) y registrar el resultado; si devuelve 404, documentar el pendiente del frontend en el reporte del apply (no bloquea: el correo degrada por wordmark).

## 5. Verificación final

- [x] 5.1 Verificar `uv lock --check`, import de la app, `uv run ruff check .`, `uv run ruff format --check .` y `uv run pytest -q` (todo verde).
- [x] 5.2 Repasar los 10 criterios de aceptación del brief contra tests y HTML generado; registrar desviaciones en el reporte del apply.
