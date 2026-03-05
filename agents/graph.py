"""
Graphe LangGraph complet — Phase 2.5
Orchestration agentique avec Memory intégrée.
"""

import structlog
from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents.planner import PlannerAgent
from agents.retriever import RetrieverAgent
from agents.generator import GeneratorAgent
from agents.tool_executor import ToolExecutorAgent
from memory.memory_manager import MemoryManager

logger = structlog.get_logger(__name__)

# Sessions mémoire (session_id → MemoryManager)
_memory_sessions: dict = {}


def get_memory(session_id: str = "default") -> MemoryManager:
    if session_id not in _memory_sessions:
        _memory_sessions[session_id] = MemoryManager(session_id=session_id)
    return _memory_sessions[session_id]


def build_graph():
    planner = PlannerAgent()
    retriever = RetrieverAgent(hybrid_candidates=20, rerank_top_k=5)
    generator = GeneratorAgent()
    tool_executor = ToolExecutorAgent()

    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner.plan)
    workflow.add_node("retriever", retriever.retrieve)
    workflow.add_node("tool_executor", tool_executor.execute)
    workflow.add_node("generate", generator.generate)

    workflow.set_entry_point("planner")

    workflow.add_conditional_edges(
        "planner",
        planner.route,
        {
            "retriever": "retriever",
            "tool_executor": "tool_executor",
            "generate": "generate",
        }
    )

    workflow.add_edge("retriever", "generate")
    workflow.add_edge("tool_executor", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


agent_graph = build_graph()


def run_agent(query: str, session_id: str = "default") -> dict:
    """Point d'entrée principal avec mémoire."""
    memory = get_memory(session_id)

    # Contexte mémoire
    memory_context = memory.get_full_context(query)

    initial_state: AgentState = {
        "query": query,
        "plan": [],
        "task_type": "",
        "retrieved_context": memory_context,
        "tool_results": [],
        "action_history": [],
        "final_response": "",
        "metadata": {"session_id": session_id},
        "iteration_count": 0,
        "errors": [],
    }

    logger.info("Démarrage agent", query=query[:80], session=session_id)
    final_state = agent_graph.invoke(initial_state)

    # Sauvegarder en mémoire
    memory.save_interaction(
        query=query,
        response=final_state.get("final_response", ""),
        metadata=final_state.get("metadata", {}),
    )

    logger.info(
        "Agent terminé",
        task_type=final_state.get("task_type"),
        session=session_id,
        response_length=len(final_state.get("final_response", "")),
    )

    return final_state