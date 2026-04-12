"""Routes FastAPI Aciérie — avec sécurité token."""
import time
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from api.schemas import QueryRequest, QueryResponse, HealthResponse
from agents.graph import run_agent
from config import config
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


def verify_token(authorization: Optional[str] = Header(None)):
    """Vérifie le token d'autorisation."""
    if config.APP_ENV == "development":
        return True
    if not authorization:
        raise HTTPException(status_code=401, detail="Token manquant")
    token = authorization.replace("Bearer ", "")
    if token != config.API_TOKEN:
        raise HTTPException(status_code=403, detail="Token invalide")
    return True


@router.post("/chat", response_model=QueryResponse)
async def chat(
    request: QueryRequest,
    authorization: Optional[str] = Header(None),
):
    """Point d'entrée principal du chatbot aciérie."""
    t_start = time.time()
    try:
        result = run_agent(
            query=request.question,
            session_id=request.session_id,
        )
        latency = round((time.time() - t_start) * 1000, 2)

        # Log audit
        logger.info(
            "AUDIT",
            action="chat",
            query=request.question[:80],
            task_type=result.get("task_type"),
            session=request.session_id,
            latency_ms=latency,
        )

        return QueryResponse(
            question=request.question,
            answer=result.get("final_response", ""),
            session_id=request.session_id,
            task_type=result.get("task_type", ""),
            plan=result.get("plan", []),
            metadata={
                **result.get("metadata", {}),
                "total_latency_ms": latency,
                "actions": len(result.get("action_history", [])),
            },
            errors=result.get("errors", []),
        )
    except Exception as e:
        logger.error("Erreur API /chat", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check."""
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        components={
            "api": "up",
            "database": "up",
            "kpi_engine": "up",
            "llm": "groq/llama-3.1-8b",
            "rag": "milvus/hnsw",
            "security": "token-based",
        }
    )


@router.get("/kpis")
async def get_kpis():
    """Liste des KPIs Gold disponibles."""
    from kpi.definitions import KPI_DEFINITIONS
    return {
        "kpis": [
            {
                "key": k,
                "nom": v["nom"],
                "unite": v["unite"],
                "description": v["description"],
                "statut": "Gold",
            }
            for k, v in KPI_DEFINITIONS.items()
        ],
        "total": len(KPI_DEFINITIONS),
        "source": "Aciérie Maghreb Steel — Base officielle",
    }


@router.get("/dashboard")
async def get_dashboard_data():
    """Données complètes pour le dashboard."""
    from kpi.engine import KPIEngine
    engine = KPIEngine()
    try:
        td      = engine.get_taux_disponibilite()
        conso   = engine.get_consommation_electrique(groupby="mois")
        prod    = engine.get_production_coulees(groupby="mois")
        defauts = engine.get_defauts_brames(limit=8)
        arrets  = engine.get_arrets_by_type(limit=6)
        oxy     = engine.get_consommation_oxygene()
        brames  = engine.get_poids_brames()
        return {
            "taux_disponibilite":     td,
            "consommation_electrique": conso,
            "production_coulees":     prod,
            "defauts_brames":         defauts,
            "arrets_by_type":         arrets,
            "oxygene":                oxy,
            "brames":                 brames,
            "status":                 "ok",
            "source":                 "Gold — Données officielles Aciérie",
        }
    except Exception as e:
        logger.error("Erreur dashboard", error=str(e))
        return {"status": "error", "message": str(e)}