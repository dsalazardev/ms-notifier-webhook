import logging
from fastapi import APIRouter, BackgroundTasks
from src.models.lead import LeadCreate
from src.services.drive_service import AsyncDriveService
from src.services.email_service import AsyncEmailService
from src.core.config import settings
from src.core.exceptions import NotificationServiceError

router = APIRouter()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

drive_service = AsyncDriveService()
email_service = AsyncEmailService()


async def process_lead_pipeline(lead: LeadCreate):
    """Caso de uso: Orquesta la descarga del Drive y el envío del correo."""
    try:
        logger.info(f"Iniciando procesamiento para {lead.email}")

        # 1. Obtener recurso
        pdf_bytes = await drive_service.get_pdf_bytes(settings.DRIVE_FILE_ID)

        # 2. Notificar al cliente
        await email_service.send_lead_email(lead.email, lead.name, pdf_bytes)

        logger.info(f"Pipeline ejecutado exitosamente para {lead.email}")

    except NotificationServiceError as e:
        # Errores controlados del dominio/infraestructura
        logger.error(f"Error controlado procesando a {lead.email}: {str(e)}")
    except Exception as e:
        # Fallos críticos no previstos
        logger.error(f"Error crítico no controlado para {lead.email}: {str(e)}")


@router.post("/lead")
async def handle_lead(lead: LeadCreate, background_tasks: BackgroundTasks):
    """
    Endpoint del Webhook que recibe los datos de la landing page.
    Retorna 202 (Accepted) inmediatamente y procesa en background.
    """
    background_tasks.add_task(process_lead_pipeline, lead)
    return {"status": "accepted", "message": "Lead recibido y procesando"}


@router.get("/health")
async def health_check():
    """Endpoint para mantener vivo el servicio en Render (cron-job ping)."""
    return {"status": "ok", "service": "ms-notifications"}