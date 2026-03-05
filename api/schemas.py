"""Schemas Pydantic pour l'API FastAPI."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    session_id: str = "default"
    top_k: int = 5


class ChunkInfo(BaseModel):
    chunk_id: str
    content: str
    score: float
    retrieval_type: str
    section: Optional[str] = ""


class QueryResponse(BaseModel):
    question: str
    answer: str
    session_id: str
    task_type: str
    plan: List[str]
    metadata: Dict[str, Any]
    errors: List[str]


class HealthResponse(BaseModel):
    status: str
    version: str
    components: Dict[str, str]


class MemoryStatsResponse(BaseModel):
    session_id: str
    stm_turns: int
    ltm_memories: int