class NotificationServiceError(Exception):
    """Excepción base para el microservicio."""
    pass

class DriveDownloadError(NotificationServiceError):
    """Lanzada cuando falla la descarga del archivo desde Google Drive."""
    pass

class EmailDeliveryError(NotificationServiceError):
    """Lanzada cuando el servidor rechaza o falla al enviar el correo."""
    pass