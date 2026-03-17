"""
Graphe LangGraph Aciérie — Orchestration complète.
Router : KPI/SQL → SQLAgent | DOC → Retriever | Direct → Generator
"""

import structlog
from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents.planner import PlannerAgent
from agents.sql_agent import SQLAgent
from agents.generator import GeneratorAgent

logger = structlog.get_logger(__name__)


def build_graph():
    planner = PlannerAgent()
    sql_agent = SQLAgent()
    generator = GeneratorAgent()

    # Retriever placeholder (RAG docs - Phase suivante)
    def retriever_placeholder(state: AgentState) -> AgentState:
        logger.info("Retriever doc appelé (placeholder)")
        return {
            **state,
            "retrieved_context": (
                "Documentation technique non encore indexée. "
                "Veuillez consulter les manuels techniques."
            ),
            "action_history": [{
                "agent": "retriever",
                "action": "placeholder",
            }],
        }

    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner.plan)
    workflow.add_node("sql_agent", sql_agent.execute)
    workflow.add_node("retriever", retriever_placeholder)
    workflow.add_node("generate", generator.generate)

    workflow.set_entry_point("planner")

    workflow.add_conditional_edges(
        "planner",
        planner.route,
        {
            "sql_agent": "sql_agent",
            "retriever": "retriever",
            "generate":  "generate",
        }
    )

    workflow.add_edge("sql_agent", "generate")
    workflow.add_edge("retriever", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


agent_graph = build_graph()


def run_agent(query: str, session_id: str = "default") -> dict:
    """Point d'entrée principal."""
    initial_state: AgentState = {
        "query": query,
        "plan": [],
        "task_type": "",
        "retrieved_context": "",
        "tool_results": [],
        "action_history": [],
        "final_response": "",
        "metadata": {"session_id": session_id},
        "iteration_count": 0,
        "errors": [],
    }

    logger.info("Agent démarré", query=query[:80], session=session_id)
    final_state = agent_graph.invoke(initial_state)
    logger.info(
        "Agent terminé",
        task_type=final_state.get("task_type"),
        response_length=len(final_state.get("final_response", "")),
    )
    return final_state