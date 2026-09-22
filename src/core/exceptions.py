class NotificationServiceError(Exception):
    """Excepción base para el microservicio."""

    retryable: bool = False

    def __init__(self, message: str = "", *, retryable: bool | None = None) -> None:
        super().__init__(message)
        if retryable is not None:
            self.retryable = retryable


class DriveDownloadError(NotificationServiceError):
    """Lanzada cuando falla la descarga del archivo desde Google Drive."""


class EmailDeliveryError(NotificationServiceError):
    """Lanzada cuando el servidor rechaza o falla al enviar el correo."""


class DocumentValidationError(NotificationServiceError):
    """Lanzada cuando el documento descargado no es un PDF válido o excede el límite."""
