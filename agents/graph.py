"""
Graphe LangGraph Aciérie — Orchestration complète.
<<<<<<< HEAD
Router : KPI/SQL → SQLAgent | DOC → RetrieverAgent RAG | Direct → DirectAnswer
=======
Router : KPI/SQL → SQLAgent | RAG → Retriever | Action → ActionAgent | Direct → Generator
>>>>>>> 610dba15115037f5f0e2c472aefa3dbb181b74e7
"""

from datetime import datetime
import structlog
from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents.planner import PlannerAgent
from agents.sql_agent import SQLAgent
from agents.retriever import RetrieverAgent
from agents.generator import GeneratorAgent
from agents.action_agent import action_app
from agents.retriever_agent import RetrieverAgent # NOUVEL IMPORT

import json
import logging
import os

os.makedirs("logs", exist_ok=True)
_audit = logging.getLogger("audit")
_audit.setLevel(logging.INFO)
if not _audit.handlers:
    _h = logging.FileHandler("logs/audit.log", encoding="utf-8")
    _h.setFormatter(logging.Formatter("%(message)s"))
    _audit.addHandler(_h)


def _log_audit(query, task_type, latency_ms, session_id, error=""):
    from datetime import datetime
    _audit.info(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "query": query[:100],
        "task_type": task_type,
        "latency_ms": latency_ms,
        "error": error,
    }, ensure_ascii=False))

logger = structlog.get_logger(__name__)

<<<<<<< HEAD

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


=======
>>>>>>> 610dba15115037f5f0e2c472aefa3dbb181b74e7
def build_graph():
    """Construit le graphe LangGraph Aciérie."""
    planner = PlannerAgent()
    sql_agent = SQLAgent()
    retriever = RetrieverAgent(top_k=5)
    generator = GeneratorAgent()
    retriever = RetrieverAgent() # INSTANCIATION DU VRAI RETRIEVER

<<<<<<< HEAD
    workflow = StateGraph(AgentState)

    workflow.add_node("planner",       planner.plan)
    workflow.add_node("sql_agent",     sql_agent.execute)
    workflow.add_node("retriever",     retriever.retrieve)
    workflow.add_node("generate",      generator.generate)
    workflow.add_node("direct_answer", direct_answer)
=======
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
>>>>>>> 610dba15115037f5f0e2c472aefa3dbb181b74e7

    workflow.set_entry_point("planner")

    workflow.add_conditional_edges(
        "planner",
        planner.route,
        {
<<<<<<< HEAD
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
=======
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
>>>>>>> 610dba15115037f5f0e2c472aefa3dbb181b74e7

    return workflow.compile()

agent_graph = build_graph()

def run_agent(query: str, session_id: str = "default") -> dict:
    from langchain_core.messages import HumanMessage
    
    initial_state: AgentState = {
<<<<<<< HEAD
        "query":             query,
        "plan":              [],
        "task_type":         "",
=======
        "messages": [HumanMessage(content=query)],
        "query": query,
        "plan": [],
        "task_type": "",
>>>>>>> 610dba15115037f5f0e2c472aefa3dbb181b74e7
        "retrieved_context": "",
        "tool_results":      [],
        "action_history":    [],
        "final_response":    "",
        "metadata":          {"session_id": session_id},
        "iteration_count":   0,
        "errors":            [],
    }

    logger.info("Agent global démarré", query=query[:80], session=session_id)
    final_state = agent_graph.invoke(initial_state)
    _log_audit(
    query=query,
    task_type=final_state.get("task_type", ""),
    latency_ms=final_state.get("metadata", {}).get("total_latency_ms", 0),
    session_id=session_id,
    error="; ".join(final_state.get("errors", [])),
)
    logger.info(
        "Agent global terminé",
        task_type=final_state.get("task_type"),
    )
    return final_state