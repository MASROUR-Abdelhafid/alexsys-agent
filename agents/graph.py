"""
Graphe LangGraph Aciérie — Orchestration complète.
Router : KPI/SQL → SQLAgent | DOC → RetrieverAgent RAG | Direct → DirectAnswer
"""

from datetime import datetime
import structlog
from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents.planner import PlannerAgent
from agents.sql_agent import SQLAgent
from agents.retriever import RetrieverAgent
from agents.generator import GeneratorAgent

logger = structlog.get_logger(__name__)


def direct_answer(state: AgentState) -> AgentState:
    """Réponse directe pour questions hors-domaine."""
    query = state["query"].lower()
    today = datetime.now().strftime("%d/%m/%Y")
    day_fr = ["Lundi","Mardi","Mercredi","Jeudi",
              "Vendredi","Samedi","Dimanche"][datetime.now().weekday()]

    if any(w in query for w in ["bonjour","salut","bonsoir","hello"]):
        answer = (
            f"Bonjour ! Je suis l'assistant KPI de l'Aciérie Maghreb Steel.\n\n"
            f"Je peux vous aider avec :\n"
            f"- **Taux de disponibilité EAF**\n"
            f"- **Consommation électrique** (EAF + LF)\n"
            f"- **Production** coulées et brames\n"
            f"- **Défauts qualité** brames\n"
            f"- **Arrêts et pannes** EAF\n"
            f"- **Documentation** procédés EAF, LF, CCM, PAF\n\n"
            f"Quelle est votre question ?"
        )
    elif any(w in query for w in ["date","jour","aujourd","on est"]):
        answer = (
            f"Nous sommes le **{day_fr} {today}**.\n\n"
            f"Comment puis-je vous aider avec les KPIs de l'aciérie ?"
        )
    elif any(w in query for w in ["heure","time","quelle heure"]):
        answer = f"Il est **{datetime.now().strftime('%H:%M')}**."
    elif any(w in query for w in ["merci","thanks"]):
        answer = "Avec plaisir ! N'hésitez pas si vous avez d'autres questions."
    elif any(w in query for w in ["au revoir","bye","bonne journée"]):
        answer = "Au revoir ! Bonne journée."
    else:
        answer = (
            "Je suis spécialisé dans les KPIs et la documentation de l'Aciérie Maghreb Steel.\n\n"
            "Je peux répondre sur la **production**, la **consommation énergétique**, "
            "les **défauts**, les **arrêts** et les **procédés** EAF/LF/CCM/PAF.\n\n"
            "Quelle est votre question ?"
        )

    return {
        **state,
        "final_response": answer,
        "action_history": [{"agent": "direct", "action": "direct_answer"}],
    }


def build_graph():
    """Construit le graphe LangGraph Aciérie."""
    planner = PlannerAgent()
    sql_agent = SQLAgent()
    retriever = RetrieverAgent(top_k=5)
    generator = GeneratorAgent()

    workflow = StateGraph(AgentState)

    workflow.add_node("planner",       planner.plan)
    workflow.add_node("sql_agent",     sql_agent.execute)
    workflow.add_node("retriever",     retriever.retrieve)
    workflow.add_node("generate",      generator.generate)
    workflow.add_node("direct_answer", direct_answer)

    workflow.set_entry_point("planner")

    workflow.add_conditional_edges(
        "planner",
        planner.route,
        {
            "sql_agent":    "sql_agent",
            "retriever":    "retriever",
            "generate":     "generate",
            "direct":       "direct_answer",
        }
    )

    workflow.add_edge("sql_agent",     "generate")
    workflow.add_edge("retriever",     "generate")
    workflow.add_edge("generate",      END)
    workflow.add_edge("direct_answer", END)

    return workflow.compile()


agent_graph = build_graph()


def run_agent(query: str, session_id: str = "default") -> dict:
    """Point d'entrée principal."""
    initial_state: AgentState = {
        "query":             query,
        "plan":              [],
        "task_type":         "",
        "retrieved_context": "",
        "tool_results":      [],
        "action_history":    [],
        "final_response":    "",
        "metadata":          {"session_id": session_id},
        "iteration_count":   0,
        "errors":            [],
    }

    logger.info("Agent démarré", query=query[:80], session=session_id)
    final_state = agent_graph.invoke(initial_state)
    logger.info(
        "Agent terminé",
        task_type=final_state.get("task_type"),
        response_length=len(final_state.get("final_response", "")),
    )
    return final_state