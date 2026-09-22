import base64
import logging

from azure.communication.email.aio import EmailClient

from src.core.config import settings
from src.core.exceptions import EmailDeliveryError

logger = logging.getLogger(__name__)


def build_lead_message(to_email: str, need: str, pdf_bytes: bytes) -> dict:
    return {
        "senderAddress": settings.FROM_EMAIL,
        "recipients": {"to": [{"address": to_email}]},
        "content": {
            "subject": "Aquí tienes tu documento y el siguiente paso",
            "plainText": f"""Hola,

Solicitaste información sobre {need}.

Gracias por tu interés. Adjunto encontrarás el PDF que solicitaste.

Me encantaría que nos reuniéramos para discutir cómo podemos ayudarte a implementar esto.
Por favor, elige el horario que mejor se adapte a ti en el siguiente enlace:
{settings.BOOKING_URL}

Quedo atento.
""",
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
