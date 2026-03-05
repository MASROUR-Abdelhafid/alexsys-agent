"""Routes FastAPI."""

import time
from fastapi import APIRouter, HTTPException
from api.schemas import (
    QueryRequest, QueryResponse,
    HealthResponse, MemoryStatsResponse,
)
from agents.graph import run_agent, get_memory
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """Point d'entrée principal — exécute le graphe agentique."""
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
                "total_api_latency_ms": latency,
                "action_count": len(result.get("action_history", [])),
            },
            errors=result.get("errors", []),
        )
    except Exception as e:
        logger.error("Erreur API /query", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check du système."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        components={
            "api": "up",
            "milvus": "up",
            "rag_pipeline": "up",
            "agents": "up",
        }
    )


@router.get("/memory/{session_id}", response_model=MemoryStatsResponse)
async def get_memory_stats(session_id: str):
    """Statistiques mémoire d'une session."""
    memory = get_memory(session_id)
    stats = memory.get_stats()
    return MemoryStatsResponse(
        session_id=session_id,
        stm_turns=stats["stm"]["turns_count"],
        ltm_memories=stats["ltm"]["total_memories"],
    )


@router.delete("/memory/{session_id}")
async def clear_memory(session_id: str):
    """Vide la mémoire court-terme d'une session."""
    memory = get_memory(session_id)
    memory.stm.clear()
    return {"status": "cleared", "session_id": session_id}