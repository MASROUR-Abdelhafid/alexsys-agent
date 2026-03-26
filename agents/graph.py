"""
Graphe LangGraph Aciérie — Orchestration complète.
Router : KPI/SQL → SQLAgent | RAG → Retriever | Action → ActionAgent | Direct → Generator
"""

import structlog
from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents.planner import PlannerAgent
from agents.sql_agent import SQLAgent
from agents.generator import GeneratorAgent
from agents.action_agent import action_app # Import du sous-graphe d'action

logger = structlog.get_logger(__name__)

def build_graph():
    planner = PlannerAgent()
    sql_agent = SQLAgent()
    generator = GeneratorAgent()

    # Retriever placeholder (RAG docs - Sera fait plus tard)
    def retriever_placeholder(state: AgentState) -> dict:
        logger.info("Retriever doc appelé (placeholder)")
        return {
            "retrieved_context": "Documentation technique non encore indexée.",
            "action_history": [{"agent": "retriever", "action": "placeholder"}],
        }

    # Wrapper pour le sous-graphe d'action afin d'adapter l'entrée/sortie si nécessaire
    def action_node(state: AgentState) -> dict:
        logger.info("Délégation au sous-graphe ActionAgent...")
        # On passe l'état actuel au sous-graphe
        result = action_app.invoke(state)
        # On récupère les messages générés par l'action agent
        return {
            "messages": result["messages"],
            "final_response": result["messages"][-1].content if result.get("messages") else "Action terminée sans retour.",
            "action_history": [{"agent": "action_agent", "action": "tool_execution"}]
        }

    workflow = StateGraph(AgentState)

    # Ajout des nœuds
    workflow.add_node("planner", planner.plan)
    workflow.add_node("sql_agent", sql_agent.execute)
    workflow.add_node("retriever", retriever_placeholder)
    workflow.add_node("action_agent", action_node) # Nouveau nœud de type Sub-graph
    workflow.add_node("generate", generator.generate)

    workflow.set_entry_point("planner")

    # Routage conditionnel depuis le planner
    workflow.add_conditional_edges(
        "planner",
        planner.route,
        {
            "sql_agent": "sql_agent",
            "retriever": "retriever",
            "action_agent": "action_agent",
            "generate":  "generate",
        }
    )

    # Connecter les experts vers le générateur ou la fin
    workflow.add_edge("sql_agent", "generate")
    workflow.add_edge("retriever", "generate")
    # L'action agent répond déjà de manière finale, on peut l'envoyer direct à la fin
    workflow.add_edge("action_agent", END) 
    workflow.add_edge("generate", END)

    return workflow.compile()

agent_graph = build_graph()

def run_agent(query: str, session_id: str = "default") -> dict:
    """Point d'entrée principal."""
    # Obligatoire : utiliser une liste vide pour 'messages' au lieu de None pour le reducer add_messages
    from langchain_core.messages import HumanMessage
    
    initial_state: AgentState = {
        "messages": [HumanMessage(content=query)],
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

    logger.info("Agent global démarré", query=query[:80], session=session_id)
    final_state = agent_graph.invoke(initial_state)
    logger.info(
        "Agent global terminé",
        task_type=final_state.get("task_type"),
    )
    return final_state