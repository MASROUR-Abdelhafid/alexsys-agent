"""
Définition des endpoints de l'API REST.
"""
import time
import structlog
from fastapi import APIRouter, HTTPException
from api.schemas import ChatRequest, ChatResponse
from agents.graph import run_agent

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    logger.info("Requete API '/chat' reçue", query=request.query, session_id=request.session_id)
    start_time = time.time()
    
    try:
        # Invocation du graphe principal LangGraph
        result = run_agent(request.query, session_id=request.session_id)
        
        latency = (time.time() - start_time) * 1000 # Conversion en millisecondes
        
        return ChatResponse(
            task_type=result.get("task_type", "unknown"),
            plan=result.get("plan", []),
            response=result.get("final_response", "Erreur: Pas de réponse finale générée par le graphe."),
            latency_ms=round(latency, 2)
        )
    except Exception as e:
        logger.error("Erreur critique dans l'API", error=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur interne de l'agent: {str(e)}")

@router.get("/health")
async def health_check():
    """Endpoint de monitoring pour vérifier que l'API est Up."""
    return {"status": "ok", "system": "Alexsys Multi-Agent RAG API"}