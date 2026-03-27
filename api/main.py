"""Application FastAPI Aciérie."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from api.routes import router

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="Aciérie Maghreb Steel — Chatbot KPI IA",
    description="Assistant IA pour les indicateurs de performance industrielle",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.on_event("startup")
async def startup():
    logger.info("API Aciérie démarrée", version="2.0.0")