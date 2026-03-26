"""
Agent Planner - Superviseur de l'architecture Multi-Agent.
Analyse la requête et détermine la route à prendre.
"""

from typing import Literal, List
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
import structlog

from agents.state import AgentState
from agents.llm_factory import get_llm

logger = structlog.get_logger(__name__)

# 1. Définition stricte de la sortie attendue par le Superviseur
class PlannerOutput(BaseModel):
    task_type: Literal["sql", "rag", "action", "direct"] = Field(
        description="""Classification stricte de la tâche:
        - 'sql' : Requêtes sur les KPI, chiffres, production, consommation (base de données).
        - 'rag' : Questions sur les procédures, manuels techniques, documentations.
        - 'action' : Demandes d'actions métier (créer un ticket CRM, générer un rapport PDF).
        - 'direct' : Salutations, discussions générales ne nécessitant pas de données industrielles."""
    )
    plan: List[str] = Field(
        description="Liste détaillée des étapes nécessaires. DOIT ABSOLUMENT être un tableau/liste JSON de chaînes de caractères (ex: ['étape 1', 'étape 2']). Ne jamais retourner une simple string."
    )

SYSTEM_PROMPT = """Tu es l'Agent Superviseur d'un système IA industriel pour une aciérie.
Ton rôle est d'analyser la demande de l'utilisateur et de la déléguer au bon spécialiste.
Réfléchis bien au contexte :
- S'il y a des calculs, des dates, des KPI (Disponibilité, Consommation) -> C'est 'sql'.
- S'il y a des notions de pannes nécessitant un technicien ou des rapports officiels -> C'est 'action'.
- S'il cherche une explication technique dans un manuel -> C'est 'rag'.
Sois précis dans ton routage.
ATTENTION CRITIQUE : Ton champ 'plan' DOIT être une liste JSON valide contenant au moins une chaîne de caractères."""

class PlannerAgent:
    def __init__(self):
        # On utilise with_structured_output pour forcer le LLM à répondre en JSON pur
        self.llm = get_llm().with_structured_output(PlannerOutput)
        
    def plan(self, state: AgentState) -> dict:
        """Évalue la requête et génère le plan d'action."""
        query = state.get("query", "")
        logger.info("Planner analyse la requête...", query=query)
        
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Requête utilisateur: {query}")
        ]
        
        try:
            # Invocation du LLM avec sortie structurée
            response: PlannerOutput = self.llm.invoke(messages)
            
            logger.info("Décision du Planner", task_type=response.task_type, plan=response.plan)
            
            # On met à jour l'état global
            return {
                "task_type": response.task_type,
                "plan": response.plan,
                "action_history": [{"agent": "planner", "action": "routing", "details": response.task_type}],
                "iteration_count": state.get("iteration_count", 0) + 1
            }
        except Exception as e:
            logger.error("Erreur de planification", error=str(e))
            # Fallback de sécurité
            return {
                "task_type": "direct",
                "plan": ["Répondre directement suite à une erreur de planification."],
                "errors": [f"Planner error: {str(e)}"]
            }

    def route(self, state: AgentState) -> str:
        """Fonction utilisée par LangGraph pour lire la décision de routage."""
        task = state.get("task_type", "direct")
        
        # Mapping entre le task_type et le nom du nœud dans le graphe
        route_map = {
            "sql": "sql_agent",
            "rag": "retriever",
            "action": "action_agent",
            "direct": "generate"
        }
        return route_map.get(task, "generate")