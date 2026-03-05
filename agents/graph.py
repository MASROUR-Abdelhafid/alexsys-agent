"""
Graphe LangGraph principal — Orchestration agentique.
Phase 2 - Étape 2.3 (Tool Executor réel intégré)
"""

import structlog
from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents.planner import PlannerAgent
from agents.retriever import RetrieverAgent
from agents.generator import GeneratorAgent
from agents.tool_executor import ToolExecutorAgent

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
    retriever = RetrieverAgent(hybrid_candidates=20, rerank_top_k=5)
    generator = GeneratorAgent()
    tool_executor = ToolExecutorAgent()

    # Construction du graphe
    workflow = StateGraph(AgentState)

    # Nœuds
    workflow.add_node("planner", planner.plan)
    workflow.add_node("retriever", retriever.retrieve)
    workflow.add_node("tool_executor", tool_executor.execute)
    workflow.add_node("generate", generator.generate)

    # Point d'entrée
    workflow.set_entry_point("planner")

    # Routing conditionnel depuis planner
    workflow.add_conditional_edges(
        "planner",
        planner.route,
        {
            "retriever": "retriever",
            "tool_executor": "tool_executor",
            "generate": "generate",
        }
    )

    # Edges fixes
    workflow.add_edge("retriever", "generate")
    workflow.add_edge("tool_executor", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


# Instance globale
agent_graph = build_graph()


def run_agent(query: str) -> dict:
    """Point d'entrée principal du système agentique."""
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
        chunks=final_state.get("metadata", {}).get(
            "rag_pipeline", {}
        ).get("chunks_reranked", 0),
        response_length=len(final_state.get("final_response", "")),
    )

    return final_state