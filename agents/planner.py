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
<<<<<<< HEAD
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

        # ✅ KPI uniquement si ce n'est PAS une question explicative
        elif is_kpi_query(query) and not any(
            w in query_lower for w in [
                "comment", "fonctionne", "fonctionnement",
                "qu est ce", "qu'est", "c'est quoi",
                "présentation", "rôle", "role", "expliquer",
                "describe", "definition", "qu est",
            ]
        ):
            task_type = "kpi"
            plan = ["Détecter KPI", "Calculer via KPIEngine", "Générer réponse"]

        # 📚 Documentation (questions explicatives)
        elif is_doc_query(query):
            task_type = "doc"
            plan = ["Rechercher dans documentation", "Générer réponse"]

        # 🤖 Cas ambigus → LLM Planner
        else:
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
=======
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
>>>>>>> 610dba15115037f5f0e2c472aefa3dbb181b74e7
