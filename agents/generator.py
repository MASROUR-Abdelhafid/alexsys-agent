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

DATE AUJOURD'HUI : {day_fr} {today}

EQUIPEMENTS :
- EAF (Four à Arc Électrique) : fusion ferraille, 120 MVA, 3 électrodes graphite
- LF (Four Poche) : affinage, désulfuration, réglage température, 20 MVA
- CCM (Coulée Continue) : solidification acier liquide en brames
- PAF (Parc à Ferraille) : stockage et préparation ferraille

REGLES STRICTES :
1. Réponds UNIQUEMENT avec les données fournies dans le contexte
2. Si aucune donnée fournie : réponds "Je n'ai pas de données officielles pour cet indicateur." puis suggère l'homologation
3. NE JAMAIS inventer ou estimer des valeurs sans données
4. NE JAMAIS afficher du SQL dans la réponse finale
5. Pour les KPIs Gold : présente la valeur principale en premier avec l'unité
6. Pour les questions documentaires : cite la source entre crochets [Source N]
7. Utilise des tirets "- " pour les listes, jamais des astérisques "*"

MARQUAGE OFFICIEL :
- KPI calculé depuis DB réelle → réponse normale
- KPI manquant dans le système → commence par "⚠️ Indicateur non homologué —" et propose de l'ajouter
- Réponse documentaire → termine par "[Source : Documentation technique Aciérie Maghreb Steel]"

FORMAT :
- Commence directement par la réponse
- Listes avec "- item" uniquement
- Maximum 5 points par liste
- Concis et professionnel"""


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