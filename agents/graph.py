"""
Graphe LangGraph principal — Orchestration agentique.
Phase 2 - Étape 2.1
"""

import structlog
from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents.planner import PlannerAgent
from agents.generator import GeneratorAgent

logger = structlog.get_logger(__name__)


def build_graph():
    """
    Construit le graphe agentique LangGraph.

    Topologie :
    START → planner → [retriever | tool_executor | generate]
                              ↓              ↓
                           generate ← ← ← ←
    """
    planner = PlannerAgent()
    generator = GeneratorAgent()

    # Nœuds placeholder pour retriever et tool_executor
    # (seront remplacés aux étapes 2.2 et 2.3)
    def retriever_placeholder(state: AgentState) -> AgentState:
        logger.info("Retriever placeholder appelé")
        return {
            **state,
            "retrieved_context": f"[Placeholder] Contexte pour : {state['query']}",
            "action_history": [{"agent": "retriever", "action": "placeholder"}],
        }

    def tool_placeholder(state: AgentState) -> AgentState:
        logger.info("Tool executor placeholder appelé")
        return {
            **state,
            "tool_results": [{"tool": "placeholder", "result": "outil non encore implémenté"}],
            "action_history": [{"agent": "tool_executor", "action": "placeholder"}],
        }

    # Construction du graphe
    workflow = StateGraph(AgentState)

    # Ajouter les nœuds
    workflow.add_node("planner", planner.plan)
    workflow.add_node("retriever", retriever_placeholder)
    workflow.add_node("tool_executor", tool_placeholder)
    workflow.add_node("generate", generator.generate)

    # Point d'entrée
    workflow.set_entry_point("planner")

    # Edges conditionnels depuis planner
    workflow.add_conditional_edges(
        "planner",
        planner.route,
        {
            "retriever": "retriever",
            "tool_executor": "tool_executor",
            "generate": "generate",
        }
    )

    # Edges fixes vers generate
    workflow.add_edge("retriever", "generate")
    workflow.add_edge("tool_executor", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


# Instance globale du graphe
agent_graph = build_graph()


def run_agent(query: str) -> dict:
    """
    Point d'entrée principal pour exécuter le graphe agentique.

    Args:
        query: question utilisateur

    Returns:
        État final avec réponse et métadonnées
    """
    initial_state: AgentState = {
        "query": query,
        "plan": [],
        "task_type": "",
        "retrieved_context": "",
        "tool_results": [],
        "action_history": [],
        "final_response": "",
        "metadata": {},
        "iteration_count": 0,
        "errors": [],
    }

    logger.info("Démarrage graphe agentique", query=query[:80])
    final_state = agent_graph.invoke(initial_state)
    logger.info(
        "Graphe terminé",
        task_type=final_state.get("task_type"),
        iterations=final_state.get("iteration_count"),
        response_length=len(final_state.get("final_response", "")),
    )

    return final_state