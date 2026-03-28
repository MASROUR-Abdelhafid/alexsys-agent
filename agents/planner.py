"""
Agent Planner — Analyse et routing des requêtes Aciérie.
Router : KPI/SQL vs RAG/DOC vs Direct
"""

import json
import time
import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from agents.state import AgentState
from agents.llm_factory import get_llm
from kpi.definitions import detect_kpi, is_kpi_query, is_doc_query
from config import config

logger = structlog.get_logger(__name__)

PLANNER_PROMPT = """Tu es un Agent Planner pour le système IA de l'Aciérie Maghreb Steel.

Analyse la question et détermine le TYPE de tâche :

TYPES :
- "kpi"  : question sur un indicateur de performance (TD%, consommation, production, défauts, arrêts)
- "sql"  : question sur les données de production nécessitant une requête SQL
- "doc"  : question sur le procédé, fonctionnement, description technique (EAF, LF, CCM, PAF)
- "direct" : question simple sans données nécessaires

Réponds UNIQUEMENT en JSON :
{
    "task_type": "kpi|sql|doc|direct",
    "plan": ["étape 1", "étape 2"],
    "reasoning": "explication courte"
}"""


class PlannerAgent:
    def __init__(self):
        self.llm = get_llm(temperature=0)
        logger.info("PlannerAgent initialisé", model=config.LLM_MODEL)

    def plan(self, state: AgentState) -> AgentState:
        """Analyse la requête et détermine le routing."""
        t_start = time.time()
        query = state["query"]
        query_lower = query.lower()
        logger.info("Planner analyse", query=query[:80])

        # Questions hors-domaine → direct avec message clair
        hors_domaine = [
            "bonjour", "bonsoir", "salut", "merci", "au revoir",
            "date", "heure", "météo", "actualité", "news",
            "blague", "poème", "histoire",
        ]
        if any(w in query_lower for w in hors_domaine) and not is_kpi_query(query):
            task_type = "direct"
            plan = ["Répondre directement"]

        elif is_kpi_query(query):
            task_type = "kpi"
            plan = ["Détecter KPI", "Calculer via KPIEngine", "Générer réponse"]

        elif is_doc_query(query):
            task_type = "doc"
            plan = ["Rechercher dans documentation", "Générer réponse"]

        else:
            # LLM pour les cas ambigus
            try:
                messages = [
                    SystemMessage(content=PLANNER_PROMPT),
                    HumanMessage(content=f"Question : {query}"),
                ]
                response = self.llm.invoke(messages)
                raw = response.content.strip()
                if "```json" in raw:
                    raw = raw.split("```json")[1].split("```")[0].strip()
                elif "```" in raw:
                    raw = raw.split("```")[1].split("```")[0].strip()
                data = json.loads(raw)
                task_type = data.get("task_type", "sql")
                plan = data.get("plan", ["Analyser", "Répondre"])
            except Exception as e:
                logger.error("Erreur Planner LLM", error=str(e))
                task_type = "sql"
                plan = ["Analyser données", "Répondre"]

        latency = round((time.time() - t_start) * 1000, 2)
        logger.info("Plan établi", task_type=task_type, latency_ms=latency)

        return {
            **state,
            "task_type": task_type,
            "plan": plan,
            "action_history": [{
                "agent": "planner",
                "action": "plan",
                "task_type": task_type,
                "latency_ms": latency,
            }],
            "iteration_count": state.get("iteration_count", 0) + 1,
        }

    def route(self, state: AgentState) -> str:
        """Route vers le bon agent."""
        task_type = state.get("task_type", "sql")
        iteration = state.get("iteration_count", 0)

        if iteration >= 5:
            return "generate"

        routing = {
            "kpi":    "sql_agent",
            "sql":    "sql_agent",
            "doc":    "retriever",
            "direct": "direct",
}
        next_node = routing.get(task_type, "sql_agent")
        logger.info("Routing vers", next_node=next_node)
        return next_node