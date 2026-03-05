"""
Agent Planner — Analyse et décomposition de requêtes.
Nœud central du graphe LangGraph.
Phase 2 - Étape 2.1
"""

import json
import time
from typing import Dict, Any

import structlog
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from agents.state import AgentState
from config import config

logger = structlog.get_logger(__name__)

# Prompt système du Planner
PLANNER_SYSTEM_PROMPT = """Tu es un Agent Planner expert pour Alexsys Solutions.

Ton rôle est d'analyser la requête utilisateur et de :
1. Identifier le TYPE de tâche
2. Décomposer en sous-tâches claires
3. Déterminer quels outils sont nécessaires

TYPES DE TÂCHES :
- "retrieval" : question sur la base de connaissances (politique, process, règles)
- "tool" : nécessite un outil externe (BDD, API, CRM, rapport PDF)
- "hybrid" : nécessite retrieval ET outils
- "direct" : question simple sans contexte nécessaire

OUTILS DISPONIBLES :
- database_query : interroger la base de données clients
- api_call : appeler une API externe
- crm_lookup : rechercher dans le CRM
- pdf_report : générer un rapport PDF

Réponds UNIQUEMENT en JSON valide avec ce format exact :
{
    "task_type": "retrieval|tool|hybrid|direct",
    "plan": ["étape 1", "étape 2", "étape 3"],
    "tools_needed": ["tool1", "tool2"],
    "reasoning": "explication courte du plan"
}"""


class PlannerAgent:
    """
    Agent Planner — Premier nœud du graphe agentique.

    Responsabilités :
    1. Analyser la requête utilisateur
    2. Classifier le type de tâche
    3. Décomposer en plan d'actions
    4. Router vers le bon agent suivant
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model=config.LLM_MODEL,
            temperature=0,
            api_key=config.OPENAI_API_KEY,
        )
        logger.info("PlannerAgent initialisé", model=config.LLM_MODEL)

    def plan(self, state: AgentState) -> AgentState:
        """
        Nœud LangGraph : analyse et planification.

        Args:
            state: état actuel du graphe

        Returns:
            état mis à jour avec plan et task_type
        """
        t_start = time.time()
        query = state["query"]

        logger.info("Planner analyse la requête", query=query[:80])

        try:
            messages = [
                SystemMessage(content=PLANNER_SYSTEM_PROMPT),
                HumanMessage(content=f"Requête : {query}"),
            ]

            response = self.llm.invoke(messages)
            raw = response.content.strip()

            # Parser JSON
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            plan_data = json.loads(raw)

            task_type = plan_data.get("task_type", "retrieval")
            plan = plan_data.get("plan", [f"Répondre à : {query}"])
            reasoning = plan_data.get("reasoning", "")

            latency = round((time.time() - t_start) * 1000, 2)

            logger.info(
                "Plan établi",
                task_type=task_type,
                steps=len(plan),
                latency_ms=latency,
            )

            return {
                **state,
                "task_type": task_type,
                "plan": plan,
                "action_history": [{
                    "agent": "planner",
                    "action": "plan",
                    "task_type": task_type,
                    "plan": plan,
                    "reasoning": reasoning,
                    "latency_ms": latency,
                }],
                "iteration_count": state.get("iteration_count", 0) + 1,
            }

        except Exception as e:
            logger.error("Erreur Planner", error=str(e))
            return {
                **state,
                "task_type": "retrieval",
                "plan": [f"Répondre à : {query}"],
                "errors": [f"Planner error: {str(e)}"],
                "iteration_count": state.get("iteration_count", 0) + 1,
            }

    def route(self, state: AgentState) -> str:
        """
        Fonction de routing — détermine le prochain nœud.

        Returns:
            nom du prochain nœud dans le graphe
        """
        task_type = state.get("task_type", "retrieval")
        iteration = state.get("iteration_count", 0)

        # Protection boucle infinie
        if iteration >= 5:
            logger.warning("Max iterations atteint", iteration=iteration)
            return "generate"

        routing_map = {
            "retrieval": "retriever",
            "tool": "tool_executor",
            "hybrid": "retriever",
            "direct": "generate",
        }

        next_node = routing_map.get(task_type, "retriever")
        logger.info("Routing vers", next_node=next_node, task_type=task_type)
        return next_node