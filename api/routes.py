"""Routes FastAPI Aciérie."""
import time
from fastapi import APIRouter, HTTPException
from api.schemas import QueryRequest, QueryResponse, HealthResponse
from agents.graph import run_agent
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/chat", response_model=QueryResponse)
async def chat(request: QueryRequest):
    """Point d'entrée principal du chatbot aciérie."""
    t_start = time.time()
    try:
        result = run_agent(
            query=request.question,
            session_id=request.session_id,
        )
        latency = round((time.time() - t_start) * 1000, 2)
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
        }
    )


@router.get("/kpis")
async def get_kpis():
    """Liste des KPIs disponibles."""
    from kpi.definitions import KPI_DEFINITIONS
    return {
        "kpis": [
            {
                "key": k,
                "nom": v["nom"],
                "unite": v["unite"],
                "description": v["description"],
            }
            for k, v in KPI_DEFINITIONS.items()
        ]
    }


@router.get("/dashboard")
async def get_dashboard_data():
    """Données complètes pour le dashboard."""
    from kpi.engine import KPIEngine
    engine = KPIEngine()

    try:
        td    = engine.get_taux_disponibilite()
        conso = engine.get_consommation_electrique(groupby="mois")
        prod  = engine.get_production_coulees(groupby="mois")
        defauts = engine.get_defauts_brames(limit=8)
        arrets  = engine.get_arrets_by_type(limit=6)
        oxy   = engine.get_consommation_oxygene()
        brames = engine.get_poids_brames()

        return {
            "taux_disponibilite":    td,
            "consommation_electrique": conso,
            "production_coulees":    prod,
            "defauts_brames":        defauts,
            "arrets_by_type":        arrets,
            "oxygene":               oxy,
            "brames":                brames,
            "status":                "ok",
        }
    except Exception as e:
        logger.error("Erreur dashboard", error=str(e))
        return {"status": "error", "message": str(e)}