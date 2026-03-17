"""
Agent Generator — Génération réponse finale Aciérie.
"""

import time
import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from agents.state import AgentState
from agents.llm_factory import get_llm

logger = structlog.get_logger(__name__)

GENERATOR_PROMPT = """Tu es un assistant expert pour l'Aciérie Maghreb Steel.

Réponds à la question en te basant UNIQUEMENT sur les données fournies.
Sois précis, professionnel et structuré.
Si les données contiennent des KPIs, présente-les clairement avec leurs unités.
Réponds en français."""


class GeneratorAgent:
    def __init__(self):
        self.llm = get_llm(temperature=0.1)
        logger.info("GeneratorAgent initialisé")

    def generate(self, state: AgentState) -> AgentState:
        """Génère la réponse finale."""
        t_start = time.time()
        query = state["query"]
        context = state.get("retrieved_context", "")
        tool_results = state.get("tool_results", [])

        tool_str = ""
        if tool_results:
            tool_str = "\nDONNÉES CALCULÉES :\n" + "\n".join(
                [str(r) for r in tool_results[:3]]
            )

        user_prompt = f"""CONTEXTE ET DONNÉES :
{context}
{tool_str}

QUESTION : {query}

Réponds de manière précise et structurée en français."""

        try:
            messages = [
                SystemMessage(content=GENERATOR_PROMPT),
                HumanMessage(content=user_prompt),
            ]
            response = self.llm.invoke(messages)
            answer = response.content.strip()
            latency = round((time.time() - t_start) * 1000, 2)

            logger.info("Réponse générée", latency_ms=latency)

            return {
                **state,
                "final_response": answer,
                "action_history": [{
                    "agent": "generator",
                    "action": "generate",
                    "latency_ms": latency,
                }],
                "metadata": {
                    **state.get("metadata", {}),
                    "generator_latency_ms": latency,
                },
            }

        except Exception as e:
            logger.error("Erreur Generator", error=str(e))
            return {
                **state,
                "final_response": f"Erreur : {str(e)}",
                "errors": [f"Generator error: {str(e)}"],
            }