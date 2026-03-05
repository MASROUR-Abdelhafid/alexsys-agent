"""Application FastAPI principale."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from api.routes import router

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="Alexsys RAG Multi-Agent API",
    description="Système d'agents IA autonomes basé sur RAG Multi-Agentique",
    version="1.0.0",
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
    logger.info("API démarrée", version="1.0.0")


@app.on_event("shutdown")
async def shutdown():
    logger.info("API arrêtée")