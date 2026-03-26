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
from agents.action_agent import action_app
from agents.retriever_agent import RetrieverAgent # NOUVEL IMPORT

logger = structlog.get_logger(__name__)

def build_graph():
    planner = PlannerAgent()
    sql_agent = SQLAgent()
    generator = GeneratorAgent()
    retriever = RetrieverAgent() # INSTANCIATION DU VRAI RETRIEVER

    def action_node(state: AgentState) -> dict:
        logger.info("Délégation au sous-graphe ActionAgent...")
        result = action_app.invoke(state)
        return {
            "messages": result["messages"],
            "final_response": result["messages"][-1].content if result.get("messages") else "Action terminée sans retour.",
            "action_history": [{"agent": "action_agent", "action": "tool_execution"}]
        }

    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner.plan)
    workflow.add_node("sql_agent", sql_agent.execute)
    workflow.add_node("retriever", retriever.retrieve) # CONNEXION DU NŒUD
    workflow.add_node("action_agent", action_node)
    workflow.add_node("generate", generator.generate)

    workflow.set_entry_point("planner")

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

    workflow.add_edge("sql_agent", "generate")
    workflow.add_edge("retriever", "generate")
    workflow.add_edge("action_agent", END) 
    workflow.add_edge("generate", END)

    return workflow.compile()

agent_graph = build_graph()

def run_agent(query: str, session_id: str = "default") -> dict:
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