from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.webhook import router as webhook_router
from src.core.config import settings
from src.core.logging import configure_logging
from src.core.rate_limit import limiter

configure_logging()

app = FastAPI(
    title="ms-notifier-webhook",
    description="Microservicio asíncrono para despachar recursos y correos a leads.",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router, prefix="/api/v1")