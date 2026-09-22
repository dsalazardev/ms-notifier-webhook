import asyncio

import google.auth.exceptions
import google.auth.transport.requests
import httpx
from google.oauth2 import service_account

from src.core.config import settings
from src.core.exceptions import DocumentValidationError, DriveDownloadError

PDF_SIGNATURE = b"%PDF-"
PDF_SIGNATURE_SCAN_BYTES = 1024
DRIVE_REQUEST_TIMEOUT_SECONDS = 15.0


def validate_pdf_bytes(
    content: bytes, *, max_bytes: int, content_length: int | None = None
) -> None:
    """Valida firma y tamaño del documento descargado (falla con DocumentValidationError)."""
    if content_length is not None and content_length > max_bytes:
        raise DocumentValidationError(
            f"El documento excede el tamaño máximo ({content_length} > {max_bytes} bytes)"
        )
    if len(content) > max_bytes:
        raise DocumentValidationError(
            f"El documento excede el tamaño máximo ({len(content)} > {max_bytes} bytes)"
        )
    if PDF_SIGNATURE not in content[:PDF_SIGNATURE_SCAN_BYTES]:
        raise DocumentValidationError("El contenido descargado no tiene firma PDF (%PDF-)")


class AsyncDriveService:
    def __init__(self) -> None:
        self.scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        self._creds: service_account.Credentials | None = None
        self._lock = asyncio.Lock()

    def _get_credentials(self) -> service_account.Credentials:
        if self._creds is None:
            self._creds = service_account.Credentials.from_service_account_info(
                settings.google_creds_dict, scopes=self.scopes
            )
        return self._creds

    async def _get_access_token(self) -> str:
        try:
            creds = self._get_credentials()
        except Exception as e:
            raise DriveDownloadError(
                f"Credenciales de Google inválidas: {e}", retryable=False
            ) from e

        if not creds.valid:
            async with self._lock:
                if not creds.valid:
                    request = google.auth.transport.requests.Request()
                    await asyncio.to_thread(creds.refresh, request)
        return creds.token

    async def get_pdf_bytes(self, file_id: str) -> bytes:
        try:
            token = await self._get_access_token()
        except google.auth.exceptions.TransportError as e:
            raise DriveDownloadError(
                f"Error de red al refrescar el token de Google: {e}", retryable=True
            ) from e
        except DriveDownloadError:
            raise
        except Exception as e:
            raise DriveDownloadError(
                f"Error al refrescar el token de Google: {e}", retryable=False
            ) from e

        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        max_bytes = settings.MAX_PDF_SIZE_MB * 1024 * 1024

        try:
            async with httpx.AsyncClient(timeout=DRIVE_REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    url, headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            retryable = status == 429 or status >= 500
            raise DriveDownloadError(
                f"Error HTTP {status} al descargar de Drive: {e}", retryable=retryable
            ) from e
        except httpx.HTTPError as e:
            raise DriveDownloadError(
                f"Error de red al descargar de Drive: {e}", retryable=True
            ) from e

        raw_length = response.headers.get("content-length")
        content_length = int(raw_length) if raw_length and raw_length.isdigit() else None
        validate_pdf_bytes(
            response.content, max_bytes=max_bytes, content_length=content_length
        )
        return response.content
