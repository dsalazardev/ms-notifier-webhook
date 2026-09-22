import base64
import logging
from html import escape as html_escape

from azure.communication.email.aio import EmailClient

from src.core.config import settings
from src.core.exceptions import EmailDeliveryError

logger = logging.getLogger(__name__)

LEAD_SUBJECT = "Tu checklist: 27 puntos para modernizar tu sistema legacy"

NAVY = "#0B2545"
NAVY_700 = "#16345E"
STEEL = "#64748B"
SURFACE = "#F8FAFC"
LINE = "#CBD5E1"
ACCENT = "#1D4ED8"
FONT_SANS = "Manrope,'Segoe UI',Arial,Helvetica,sans-serif"
FONT_MONO = "ui-monospace,'JetBrains Mono',Consolas,monospace"


def _render_lead_html(*, need: str, booking_url: str, whatsapp_url: str, logo_url: str) -> str:
    """Renderiza el correo HTML branded (tablas, CSS inline, sin JS/base64/fuentes)."""
    safe_need = html_escape(need)
    safe_booking = html_escape(booking_url, quote=True)
    safe_whatsapp = html_escape(whatsapp_url, quote=True)
    safe_logo = html_escape(logo_url, quote=True)
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{LEAD_SUBJECT}</title>
</head>
<body style="margin:0; padding:0; background-color:{SURFACE};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{SURFACE};">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px; max-width:600px; background-color:#FFFFFF; border:1px solid {LINE}; border-radius:6px;">
<tr>
<td align="center" bgcolor="{NAVY}" style="background-color:{NAVY}; padding:32px 24px;">
<img src="{safe_logo}" alt="SALAZAR Eng." width="72" height="62" style="display:block; width:72px; height:62px; border:0; outline:none;">
<div style="font-family:{FONT_SANS}; font-size:16px; font-weight:700; color:#FFFFFF; padding-top:12px;">SALAZAR Eng.</div>
<div style="font-family:{FONT_MONO}; font-size:10px; letter-spacing:0.22em; text-transform:uppercase; color:rgba(255,255,255,0.62); padding-top:6px;">SALAZAR ENG. · RECURSO GRATUITO</div>
</td>
</tr>
<tr>
<td style="padding:32px 40px 0 40px; font-family:{FONT_SANS}; font-size:22px; line-height:1.3; font-weight:700; color:{NAVY};">Checklist: 27 puntos para modernizar tu sistema legacy</td>
</tr>
<tr>
<td style="padding:18px 40px 0 40px;"><div style="border-top:1px solid {LINE}; font-size:0; line-height:0;">&nbsp;</div></td>
</tr>
<tr>
<td style="padding:20px 40px 0 40px; font-family:{FONT_SANS}; font-size:15px; line-height:1.6; color:{NAVY_700};">
<p style="margin:0 0 12px 0;">Solicitaste información sobre <strong style="color:{NAVY};">{safe_need}</strong>.</p>
<p style="margin:0;">Encontrarás adjunto el documento que pediste: <strong style="color:{NAVY};">Checklist-27-puntos-SALAZAR-Eng.pdf</strong>.</p>
</td>
</tr>
<tr>
<td align="center" style="padding:28px 40px 4px 40px;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
<td align="center" bgcolor="{ACCENT}" style="background-color:{ACCENT}; border-radius:6px;">
<a href="{safe_booking}" style="display:inline-block; padding:14px 28px; font-family:{FONT_SANS}; font-size:15px; font-weight:700; color:#FFFFFF; text-decoration:none;">Agenda tu diagnóstico · 20 min</a>
</td>
</tr></table>
</td>
</tr>
<tr>
<td style="padding:24px 40px 0 40px; font-family:{FONT_SANS}; font-size:15px; line-height:1.6; color:{NAVY_700};">— SALAZAR Eng. · Software &amp; Applied AI</td>
</tr>
<tr>
<td style="padding:20px 40px 32px 40px; font-family:{FONT_SANS}; font-size:12px; line-height:1.6; color:{STEEL}; border-top:1px solid {LINE};">
<p style="margin:0 0 8px 0;">Este correo se envió automáticamente desde una dirección que no recibe respuestas.</p>
<p style="margin:0 0 8px 0;">Agenda tu diagnóstico: <a href="{safe_booking}" style="color:{ACCENT};">elegir horario</a>.</p>
<p style="margin:0;">¿Prefieres WhatsApp? <a href="{safe_whatsapp}" style="color:{ACCENT};">wa.me/573145919465</a>.</p>
</td>
</tr>
</table>
</td></tr>
</table>
</body>
</html>
"""


def build_lead_message(to_email: str, need: str, pdf_bytes: bytes) -> dict:
    html = _render_lead_html(
        need=need,
        booking_url=settings.BOOKING_URL,
        whatsapp_url=settings.LEAD_EMAIL_WHATSAPP_URL,
        logo_url=settings.LEAD_EMAIL_LOGO_URL,
    )
    return {
        "senderAddress": settings.FROM_EMAIL,
        "recipients": {"to": [{"address": to_email}]},
        "content": {
            "subject": LEAD_SUBJECT,
            "plainText": f"""Hola,

Solicitaste información sobre {need}.

Encontrarás adjunto el documento que pediste: Checklist-27-puntos-SALAZAR-Eng.pdf.

Agenda tu diagnóstico · 20 min:
{settings.BOOKING_URL}

¿Prefieres WhatsApp? Escríbeme: {settings.LEAD_EMAIL_WHATSAPP_URL}

— SALAZAR Eng. · Software & Applied AI

Este correo se envió automáticamente desde una dirección que no recibe respuestas.
""",
            "html": html,
        },
        "attachments": [
            {
                "name": "Checklist-27-puntos-SALAZAR-Eng.pdf",
                "contentType": "application/pdf",
                "contentInBase64": base64.b64encode(pdf_bytes).decode("utf-8"),
            }
        ],
    }


def build_alert_message(lead_email: str, phase: str, error_summary: str) -> dict:
    alert_to = str(settings.ALERT_EMAIL) if settings.ALERT_EMAIL else settings.FROM_EMAIL
    return {
        "senderAddress": settings.FROM_EMAIL,
        "recipients": {"to": [{"address": alert_to}]},
        "content": {
            "subject": "Fallo en el pipeline de leads (ms-notifier-webhook)",
            "plainText": (
                "El pipeline falló de forma definitiva.\n\n"
                f"Lead: {lead_email}\n"
                f"Fase: {phase}\n"
                f"Error: {error_summary}\n"
            ),
        },
    }


class AsyncEmailService:
    def __init__(self) -> None:
        self.connection_string = settings.AZURE_EMAIL_CONNECTION_STRING.get_secret_value()

    async def send_lead_email(self, to_email: str, need: str, pdf_bytes: bytes) -> None:
        message = build_lead_message(to_email, need, pdf_bytes)
        await self._send(message, context=f"lead {to_email}")

    async def send_alert_email(self, lead_email: str, phase: str, error_summary: str) -> None:
        message = build_alert_message(lead_email, phase, error_summary)
        try:
            await self._send(message, context="alerta al dueño")
        except EmailDeliveryError as e:
            logger.critical("alert.send_failed error=%s", e)

    async def _send(self, message: dict, *, context: str) -> None:
        try:
            client = EmailClient.from_connection_string(self.connection_string)
            async with client:
                poller = await client.begin_send(message)
                result = await poller.result()
        except Exception as e:
            raise EmailDeliveryError(
                f"Fallo al enviar correo ({context}): {e}", retryable=True
            ) from e

        if result.get("status") == "Failed":
            error_msg = result.get("error", {}).get("message", "Error desconocido en Azure")
            raise EmailDeliveryError(
                f"Azure rechazó el correo ({context}): {error_msg}", retryable=False
            )
