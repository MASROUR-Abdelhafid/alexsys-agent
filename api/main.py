<<<<<<< HEAD
"""Application FastAPI Aciérie."""
=======
"""
Point d'entrée de l'application FastAPI.
"""
>>>>>>> 610dba15115037f5f0e2c472aefa3dbb181b74e7
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router

<<<<<<< HEAD
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


logger = structlog.get_logger(__name__)

app = FastAPI(
    title="Aciérie Maghreb Steel — Chatbot KPI IA",
    description="Assistant IA pour les indicateurs de performance industrielle",
    version="2.0.0",
)
=======
def create_app() -> FastAPI:
    app = FastAPI(
        title="Alexsys Agent API",
        description="API REST du système autonome Multi-Agent pour l'aciérie.",
        version="1.0.0"
    )

    # Configuration CORS OBLIGATOIRE pour permettre au Frontend React (ex: port 3000 ou 5173) de faire des requêtes
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # En production, remplacer "*" par l'URL exacte du frontend
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
>>>>>>> 610dba15115037f5f0e2c472aefa3dbb181b74e7

    # Montage des routes sous le préfixe /api/v1
    app.include_router(router, prefix="/api/v1")

    return app

<<<<<<< HEAD
@app.on_event("startup")
async def startup():
    logger.info("API Aciérie démarrée", version="2.0.0")
=======
app = create_app()
>>>>>>> 610dba15115037f5f0e2c472aefa3dbb181b74e7
