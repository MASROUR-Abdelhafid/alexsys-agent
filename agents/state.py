"""
État partagé du graphe agentique.
Toutes les données transitent via cet objet.
Phase 2 - Étape 2.1
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
import operator


class AgentState(TypedDict):
    """
    État global partagé entre tous les nœuds du graphe.

    Chaque nœud lit et/ou modifie cet état.
    Les listes utilisent operator.add pour accumulation.
    """

    # Requête utilisateur originale
    query: str

    # Plan décomposé par le Planner
    plan: List[str]

    # Type de tâche détecté
    task_type: str  # "retrieval" | "tool" | "hybrid" | "direct"

    # Contexte RAG récupéré
    retrieved_context: str

    # Résultats des outils
    tool_results: Annotated[List[Dict[str, Any]], operator.add]

    # Historique des actions (pour debug et monitoring)
    action_history: Annotated[List[Dict[str, Any]], operator.add]

    # Réponse finale générée
    final_response: str

    # Métriques de performance
    metadata: Dict[str, Any]

    # Nombre d'itérations (protection boucle infinie)
    iteration_count: int

    # Erreurs éventuelles
    errors: Annotated[List[str], operator.add]