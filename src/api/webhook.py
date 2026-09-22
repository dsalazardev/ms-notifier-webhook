import logging

from fastapi import APIRouter, BackgroundTasks, Request, Response
from fastapi.responses import JSONResponse
from limits import parse as parse_limit

from src.core.config import settings
from src.core.exceptions import NotificationServiceError
from src.core.rate_limit import limiter
from src.core.retry import run_with_retries
from src.models.lead import LeadCreate
from src.services.drive_service import AsyncDriveService
from src.services.email_service import AsyncEmailService

router = APIRouter()
logger = logging.getLogger(__name__)

drive_service = AsyncDriveService()
email_service = AsyncEmailService()


def _retry_logger(lead_email: str, phase: str):
    def _log(attempt: int, exc: Exception) -> None:
        logger.warning(
            "pipeline.retry lead=%s phase=%s attempt=%s error=%s",
            lead_email,
            phase,
            attempt,
            exc,
        )

    return _log


async def process_lead_pipeline(lead: LeadCreate) -> None:
    """Caso de uso: orquesta la descarga y el envío con retries y alerta ante fallo."""
    phase = "drive.download"
    try:
        logger.info("pipeline.start lead=%s", lead.email)

        pdf_bytes = await run_with_retries(
            lambda: drive_service.get_pdf_bytes(settings.DRIVE_FILE_ID),
            on_retry=_retry_logger(lead.email, phase),
        )

        phase = "email.send"
        await run_with_retries(
            lambda: email_service.send_lead_email(lead.email, lead.need, pdf_bytes),
            on_retry=_retry_logger(lead.email, phase),
        )

        logger.info("pipeline.success lead=%s", lead.email)
    except NotificationServiceError as e:
        logger.error("pipeline.failed lead=%s phase=%s error=%s", lead.email, phase, e)
        await _send_failure_alert(lead, phase, e)
    except Exception as e:
        logger.error("pipeline.unexpected lead=%s phase=%s error=%s", lead.email, phase, e)
        await _send_failure_alert(lead, phase, e)


async def _send_failure_alert(lead: LeadCreate, phase: str, error: Exception) -> None:
    try:
        await email_service.send_alert_email(lead.email, phase, str(error))
    except Exception as e:
        logger.critical("alert.send_failed lead=%s phase=%s error=%s", lead.email, phase, e)


def _lead_rate_limit() -> str:
    return settings.RATE_LIMIT_LEAD


@router.post("/lead", status_code=202)
@limiter.limit(_lead_rate_limit)
async def handle_lead(
    request: Request,
    response: Response,
    lead: LeadCreate,
    background_tasks: BackgroundTasks,
):
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
