from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.webhook import router as webhook_router
from src.core.config import settings

app = FastAPI(
    title="ms-notifier-webhook",
    description="Microservicio asíncrono para despachar recursos y correos a leads.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router, prefix="/api/v1")