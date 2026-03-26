"""
Point d'entrée de l'application FastAPI.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router

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

    # Montage des routes sous le préfixe /api/v1
    app.include_router(router, prefix="/api/v1")

    return app

app = create_app()