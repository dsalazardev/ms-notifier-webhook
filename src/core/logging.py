import logging

from src.core.config import settings

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging() -> None:
    """Configura el logging raíz según LOG_LEVEL (idempotente)."""
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL.upper())
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root.addHandler(handler)
