import base64
from azure.communication.email.aio import EmailClient
from src.core.config import settings
from src.core.exceptions import EmailDeliveryError


class AsyncEmailService:
    def __init__(self):
        self.connection_string = settings.AZURE_EMAIL_CONNECTION_STRING.get_secret_value()

    async def send_lead_email(self, to_email: str, need: str, pdf_bytes: bytes):
        message = {
            "senderAddress": settings.FROM_EMAIL,
            "recipients": {
                "to": [{"address": to_email}]
            },
            "content": {
                "subject": "Aquí tienes tu documento y el siguiente paso",
                "plainText": f"""Hola {to_email} solicitaste información sobre {need}.,

Gracias por tu interés. Adjunto encontrarás el PDF que solicitaste.

Me encantaría que nos reuniéramos para discutir cómo podemos ayudarte a implementar esto. 
Por favor, elige el horario que mejor se adapte a ti en el siguiente enlace:
{settings.BOOKING_URL}

Quedo atento.
"""
            },
            "attachments": [
                {
                    "name": "Documento_Especial.pdf",
                    "contentType": "application/pdf",
                    "contentInBase64": base64.b64encode(pdf_bytes).decode('utf-8')
                }
            ]
        }

        try:
            client = EmailClient.from_connection_string(self.connection_string)

            async with client:
                poller = await client.begin_send(message)

                result = await poller.result()

                if result.get("status") == "Failed":
                    error_msg = result.get("error", {}).get("message", "Error desconocido en Azure")
                    raise EmailDeliveryError(f"Azure rechazó el correo: {error_msg}")

        except Exception as e:
            raise EmailDeliveryError(f"Fallo crítico al conectar con Azure Email para {to_email}: {str(e)}")