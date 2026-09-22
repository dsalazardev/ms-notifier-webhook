import httpx
from google.oauth2 import service_account
import google.auth.transport.requests
from src.core.config import settings
from src.core.exceptions import DriveDownloadError


class AsyncDriveService:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/drive.readonly']
        self.creds = service_account.Credentials.from_service_account_info(
            settings.google_creds_dict, scopes=self.scopes
        )

    def _get_access_token(self) -> str:
        request = google.auth.transport.requests.Request()
        self.creds.refresh(request)
        return self.creds.token

    async def get_pdf_bytes(self, file_id: str) -> bytes:
        token = self._get_access_token()
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
                return response.content
        except httpx.HTTPError as e:
            raise DriveDownloadError(f"Error HTTP al descargar de Drive: {str(e)}")
        except Exception as e:
            raise DriveDownloadError(f"Error inesperado en Drive: {str(e)}")