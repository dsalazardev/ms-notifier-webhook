from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.webhook import router as webhook_router

app = FastAPI(
    title="ms-notifications",
    description="Microservicio asíncrono para despachar recursos y correos a leads.",
    version="1.0.0"
)

# Configuración de CORS
origins = [
    "http://localhost:4321",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router, prefix="/api/v1")