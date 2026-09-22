import logging

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse
from limits import parse as parse_limit

from src.core.config import settings
from src.core.exceptions import NotificationServiceError
from src.models.lead import LeadCreate
from src.services.drive_service import AsyncDriveService
from src.services.email_service import AsyncEmailService

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
        await email_service.send_lead_email(lead.email, lead.need, pdf_bytes)

        logger.info(f"Pipeline ejecutado exitosamente para {lead.email}")

    except NotificationServiceError as e:
        # Errores controlados del dominio/infraestructura
        logger.error(f"Error controlado procesando a {lead.email}: {str(e)}")
    except Exception as e:
        # Fallos críticos no previstos
        logger.error(f"Error crítico no controlado para {lead.email}: {str(e)}")


@router.post("/lead", status_code=202)
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
    return {"status": "ok", "service": "ms-notifier-webhook"}


@router.get("/health/ready")
async def readiness_check():
    """Readiness: valida la configuración crítica sin llamadas externas."""
    checks: dict[str, bool] = {}

    try:
        creds = settings.google_creds_dict
        checks["google_credentials_json"] = isinstance(creds, dict) and bool(creds)
    except Exception:
        checks["google_credentials_json"] = False

    checks["drive_file_id"] = bool(settings.DRIVE_FILE_ID.strip())
    checks["azure_connection_string"] = bool(
        settings.AZURE_EMAIL_CONNECTION_STRING.get_secret_value().strip()
    )
    checks["cors_origins"] = bool(settings.CORS_ORIGINS)
    checks["max_pdf_size_mb"] = settings.MAX_PDF_SIZE_MB > 0

    try:
        parse_limit(settings.RATE_LIMIT_LEAD)
        checks["rate_limit_lead"] = True
    except Exception:
        checks["rate_limit_lead"] = False

    ready = all(checks.values())
    payload = {"status": "ready" if ready else "not_ready", "checks": checks}
    return JSONResponse(status_code=200 if ready else 503, content=payload)