"""Schemas Pydantic API Aciérie."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    session_id: str = "default"


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