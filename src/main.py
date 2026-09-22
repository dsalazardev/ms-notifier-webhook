from fastapi import FastAPI
from src.api.webhook import router as webhook_router

app = FastAPI(
    title="ms-notifications",
    description="Microservicio asíncrono para despachar recursos y correos a leads.",
    version="1.0.0"
)

app.include_router(webhook_router, prefix="/api/v1")