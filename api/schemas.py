<<<<<<< HEAD
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
=======
"""
Schémas Pydantic pour l'API REST.
"""
from pydantic import BaseModel, Field
from typing import List, Optional

class ChatRequest(BaseModel):
    query: str = Field(..., description="La question ou commande de l'utilisateur")
    session_id: Optional[str] = Field("default_session", description="ID de session pour la mémoire (optionnel)")

class ChatResponse(BaseModel):
    task_type: str = Field(..., description="Le type de tâche détecté par le superviseur (sql, rag, action, direct)")
    plan: List[str] = Field(..., description="Le plan d'action généré par le superviseur")
    response: str = Field(..., description="La réponse finale textuelle de l'Agent")
    latency_ms: Optional[float] = Field(None, description="Temps de traitement côté backend en millisecondes")
>>>>>>> 610dba15115037f5f0e2c472aefa3dbb181b74e7
