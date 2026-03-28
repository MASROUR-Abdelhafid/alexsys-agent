"""
Agent Generator — Génération réponse finale Aciérie.
"""

import time
from datetime import datetime
import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from agents.state import AgentState
from agents.llm_factory import get_llm

logger = structlog.get_logger(__name__)


def get_system_prompt():
    today = datetime.now().strftime("%d/%m/%Y")
    day_fr = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"][datetime.now().weekday()]
    return f"""Tu es un assistant expert en KPIs industriels pour l'Aciérie Maghreb Steel (Maroc).

📅 DATE AUJOURD'HUI : {day_fr} {today}

🏭 TU CONNAIS CES ÉQUIPEMENTS :
- EAF (Four à Arc Électrique) : fusion ferraille → acier liquide
- LF (Four Poche) : affinage, désulfuration, réglage température
- CCM (Coulée Continue) : solidification acier → brames
- PAF (Parc à Ferraille) : stockage et préparation ferraille

📊 RÈGLES STRICTES :
1. Réponds UNIQUEMENT avec les données fournies dans le contexte
2. Si aucune donnée n'est fournie, dis-le clairement et simplement
3. NE JAMAIS inventer ou estimer des valeurs
4. NE JAMAIS afficher du SQL ou du code dans ta réponse finale
5. Sois concis et direct — pas de phrases inutiles
6. Utilise des unités correctes (MWh, %, tonnes, coulées)
7. Pour les KPIs, présente la valeur principale en premier

🗣️ FORMAT DE RÉPONSE :
- Commence directement par la réponse
- Utilise des listes à puces pour les détails
- Maximum 3-4 lignes pour une réponse simple
- Pas de "Je suis ravi", "Bien sûr", ni de formules de politesse inutiles"""


class GeneratorAgent:
    def __init__(self):
        self.llm = get_llm(temperature=0)
        logger.info("GeneratorAgent initialisé")

    def generate(self, state: AgentState) -> AgentState:
        """Génère la réponse finale."""
        t_start = time.time()
        query = state["query"]
        context = state.get("retrieved_context", "")
        tool_results = state.get("tool_results", [])

        # Construire contexte données
        data_context = ""
        if context and context.strip():
            data_context = f"\n\n📊 DONNÉES CALCULÉES :\n{context}"

        if tool_results:
            import json
            data_context += "\n\n🔢 RÉSULTATS BRUTS :\n"
            for r in tool_results[:2]:
                if isinstance(r, dict) and "error" not in r:
                    data_context += json.dumps(r, ensure_ascii=False, indent=2)[:500]

        if not data_context.strip():
            data_context = "\n\n⚠️ Aucune donnée disponible pour cette question."

        user_prompt = f"""QUESTION : {query}
{data_context}

Réponds directement et concisément en français."""

        try:
            messages = [
                SystemMessage(content=get_system_prompt()),
                HumanMessage(content=user_prompt),
            ]
            response = self.llm.invoke(messages)
            answer = response.content.strip()

            # Nettoyer les réponses parasites
            answer = answer.replace("Réponse :", "").strip()

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
                "final_response": f"Erreur lors de la génération : {str(e)}",
                "errors": [f"Generator error: {str(e)}"],
            }