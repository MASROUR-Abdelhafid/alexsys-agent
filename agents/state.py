"""
État partagé du graphe agentique.
Phase Aciérie
"""

from typing import TypedDict, List, Dict, Any, Annotated
import operator
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """État global partagé entre tous les nœuds du graphe."""

    # --- Requis pour le pattern ReAct (ToolNode) ---
    messages: Annotated[list[BaseMessage], add_messages]

    # Requête utilisateur
    query: str

    # Plan décomposé par le Planner
    plan: List[str]

    # Type de tâche : "kpi" | "sql" | "rag" | "doc" | "direct"
    task_type: str

    # Contexte récupéré (RAG ou SQL)
    retrieved_context: str

    # Résultats des outils/KPI
    tool_results: Annotated[List[Dict[str, Any]], operator.add]

    # Historique des actions
    action_history: Annotated[List[Dict[str, Any]], operator.add]

    # Réponse finale
    final_response: str

    # Métadonnées et métriques
    metadata: Dict[str, Any]

    # Compteur d'itérations
    iteration_count: int

    # Erreurs
    errors: Annotated[List[str], operator.add]