"""
Agent Generator — Génération de la réponse finale.
Phase 2 - Étape 2.1
"""

import time
from typing import Dict, Any
import structlog
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from agents.state import AgentState
from config import config

logger = structlog.get_logger(__name__)

GENERATOR_SYSTEM_PROMPT = """Tu es un assistant expert pour Alexsys Solutions.

Réponds à la question de l'utilisateur en te basant UNIQUEMENT sur le contexte fourni.
Si le contexte ne contient pas la réponse, dis-le clairement.
Sois précis, structuré et professionnel.
Réponds en français."""


class GeneratorAgent:
    """Génère la réponse finale à partir du contexte récupéré."""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=config.LLM_MODEL,
            temperature=0.1,
            api_key=config.OPENAI_API_KEY,
        )
        logger.info("GeneratorAgent initialisé")

    def generate(self, state: AgentState) -> AgentState:
        """Nœud LangGraph : génération réponse finale."""
        t_start = time.time()
        query = state["query"]
        context = state.get("retrieved_context", "")
        tool_results = state.get("tool_results", [])

        # Construire le prompt
        context_str = context if context else "Aucun contexte RAG disponible."
        tool_str = ""
        if tool_results:
            tool_str = "\n\nRÉSULTATS OUTILS :\n" + "\n".join(
                [f"- {r.get('tool', '')}: {r.get('result', '')}"
                 for r in tool_results]
            )

        user_prompt = f"""CONTEXTE :
{context_str}
{tool_str}

QUESTION : {query}

Réponds de manière précise et structurée."""

        try:
            messages = [
                SystemMessage(content=GENERATOR_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]
            response = self.llm.invoke(messages)
            answer = response.content.strip()
            latency = round((time.time() - t_start) * 1000, 2)

            logger.info("Réponse générée", latency_ms=latency, length=len(answer))

            return {
                **state,
                "final_response": answer,
                "action_history": [{
                    "agent": "generator",
                    "action": "generate",
                    "latency_ms": latency,
                    "response_length": len(answer),
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
                "final_response": f"Erreur lors de la génération : {str(e)}",
                "errors": [f"Generator error: {str(e)}"],
            }