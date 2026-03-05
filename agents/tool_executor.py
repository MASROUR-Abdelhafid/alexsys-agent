"""
Agent Tool Executor — Orchestration des outils.
Phase 2 - Étape 2.3
"""

import time
from typing import Dict, Any
import structlog

from agents.state import AgentState
from tools.api_tool import call_external_api
from tools.database_tool import (
    init_database, query_database,
    get_premium_clients, get_open_tickets,
)
from tools.crm_tool import crm_lookup, get_at_risk_clients
from tools.pdf_generator import generate_pdf_report

logger = structlog.get_logger(__name__)


class ToolExecutorAgent:
    """
    Agent Tool Executor — Sélectionne et exécute les outils.
    """

    def __init__(self):
        init_database()
        logger.info("ToolExecutorAgent initialisé")

    def _select_tool(self, query: str, plan: list) -> str:
        query_lower = query.lower()
        plan_str = " ".join(plan).lower()
        combined = query_lower + " " + plan_str

        if any(w in combined for w in ["pdf", "rapport", "report", "génère", "générer"]):
            return "pdf_report"
        elif any(w in combined for w in ["crm", "contact", "santé", "health", "risque"]):
            return "crm_lookup"
        elif any(w in combined for w in ["base", "sql", "ticket", "client", "données"]):
            return "database_query"
        else:
            return "api_call"

    def execute(self, state: AgentState) -> AgentState:
        """Nœud LangGraph : exécution des outils."""
        t_start = time.time()
        query = state["query"]
        plan = state.get("plan", [])

        tool_name = self._select_tool(query, plan)
        logger.info("Tool sélectionné", tool=tool_name, query=query[:60])

        try:
            if tool_name == "pdf_report":
                clients = get_premium_clients()
                result = generate_pdf_report(
                    title="Rapport Clients Premium — Alexsys Solutions",
                    sections=[
                        {
                            "heading": "Clients Premium Actifs",
                            "content": clients.get("result", []),
                        },
                        {
                            "heading": "Synthèse",
                            "content": f"Total clients Premium : {clients.get('row_count', 0)}",
                        },
                    ],
                )
            elif tool_name == "crm_lookup":
                result = get_at_risk_clients()
            elif tool_name == "database_query":
                if "ticket" in query.lower():
                    result = get_open_tickets()
                else:
                    result = get_premium_clients()
            else:
                if "stat" in query.lower() or "kpi" in query.lower():
                    result = call_external_api("/stats")
                elif "contrat" in query.lower():
                    result = call_external_api("/contracts")
                else:
                    result = call_external_api("/clients")

            latency = round((time.time() - t_start) * 1000, 2)

            return {
                **state,
                "tool_results": [result],
                "action_history": [{
                    "agent": "tool_executor",
                    "action": "execute_tool",
                    "tool": tool_name,
                    "latency_ms": latency,
                }],
                "metadata": {
                    **state.get("metadata", {}),
                    "tool_latency_ms": latency,
                    "tool_used": tool_name,
                },
            }

        except Exception as e:
            logger.error("Erreur ToolExecutor", error=str(e))
            return {
                **state,
                "tool_results": [{"tool": tool_name, "error": str(e)}],
                "errors": [f"ToolExecutor error: {str(e)}"],
                "action_history": [{
                    "agent": "tool_executor",
                    "action": "error",
                    "error": str(e),
                }],
            }