"""
Agent SQL — Interprétation questions → KPI/SQL Aciérie.
Phase Aciérie
"""

import re
import time
from typing import Dict, Any
import structlog

from agents.state import AgentState
from kpi.engine import KPIEngine
from kpi.definitions import detect_kpi, KPI_DEFINITIONS
from agents.llm_factory import get_llm
from langchain_core.messages import HumanMessage, SystemMessage

logger = structlog.get_logger(__name__)

SQL_AGENT_PROMPT = """Tu es un expert SQL spécialisé dans les KPIs d'une aciérie (Maghreb Steel).

Base de données SQLite avec ces tables :
- EAF        : Four à Arc Électrique (HEATID, TREATID, STEELGRADECODE_ACT, HEATANNOUNCE_ACT, HEATDEPARTURE_ACT, TOTAL_ELEC_EGY, TAPPING_WEIGHT, BURNER_TOTALOXY, BURNER_TOTALGAS, INJ_CARBON)
- LF         : Four Poche (HEATID, TREATID, STEELGRADECODE_ACT, HEATANNOUNCE_ACT, HEATDEPARTURE_ACT, ELEC_CONS_TOTAL, STIRR_AR_CONS, STIRR_N2_CONS)
- EAF_Arrets : Arrêts EAF (HEATID, DELAYSTART, DELAYEND, DURATION, DELAYDESCR, GROUPNAME, SECTIONNAME)
- CCM_Coulee : Coulée Continue (HEATID, GRADE_CODE, LADLE_ARRIVAL_TIME, LADLE_OPEN_TIME, LADLE_CLOSE_TIME, LADLE_OPEN_WEIGHT)
- CCM_Brame  : Brames (SLAB_STEEL_ID, PIECE_WEIGHT_MEAS, NOMINAL_THICKNESS, NOMINAL_WIDTH_HEAD, PIECE_LENGTH, CUT_TIME)
- Defauts_Brame : Défauts (DFB_NUM_COULEE, DFB_NUM_BRAME, DFB_GRAVITE, DFT_NOM)
- PAF        : Parc à Ferraille (CSO_DATE, CSO_NUM_COULEE, CSO_GRADE, CSD_POIDS, FERR_NOM, CAT_NOM)

Règles STRICTES :
1. Génère UNIQUEMENT des requêtes SELECT
2. Limite à 10 résultats sauf demande explicite
3. Utilise ROUND() pour les décimaux
4. Utilise COALESCE() pour les NULL
5. Réponds UNIQUEMENT avec le SQL, rien d'autre
6. Pas de markdown, pas d'explication

Question : {question}

SQL :"""


class SQLAgent:
    """
    Agent SQL Aciérie.
    Deux modes :
    1. KPI prédéfini → KPIEngine (précis, optimisé)
    2. Question libre → LLM génère SQL (flexible)
    """

    def __init__(self):
        self.kpi_engine = KPIEngine()
        self.llm = get_llm(temperature=0)
        logger.info("SQLAgent initialisé")

    def _extract_period_params(self, query: str) -> Dict[str, Any]:
        """Extrait les paramètres de période depuis la query."""
        params = {"groupby": "total", "date_debut": None, "date_fin": None, "grade": None}

        query_lower = query.lower()

        if "par jour" in query_lower or "journalier" in query_lower:
            params["groupby"] = "jour"
        elif "par semaine" in query_lower or "hebdomadaire" in query_lower:
            params["groupby"] = "semaine"
        elif "par mois" in query_lower or "mensuel" in query_lower:
            params["groupby"] = "mois"
        elif "par grade" in query_lower or "grade" in query_lower:
            params["groupby"] = "grade"

        # Extraction grade
        grade_match = re.search(r'\b([A-Z]{2,4}\d{3,}[A-Z0-9]*)\b', query)
        if grade_match:
            params["grade"] = grade_match.group(1)

        return params

    def _handle_kpi(self, kpi_key: str, query: str) -> Dict[str, Any]:
        """Exécute un KPI prédéfini."""
        params = self._extract_period_params(query)

        try:
            if kpi_key == "taux_disponibilite":
                return self.kpi_engine.get_taux_disponibilite(
                    params.get("date_debut"),
                    params.get("date_fin"),
                )
            elif kpi_key == "consommation_electrique":
                return self.kpi_engine.get_consommation_electrique(
                    groupby=params["groupby"],
                    date_debut=params.get("date_debut"),
                    date_fin=params.get("date_fin"),
                    grade=params.get("grade"),
                )
            elif kpi_key == "production_coulees":
                return self.kpi_engine.get_production_coulees(
                    groupby=params["groupby"],
                    date_debut=params.get("date_debut"),
                    date_fin=params.get("date_fin"),
                )
            elif kpi_key == "defauts_brames":
                return self.kpi_engine.get_defauts_brames(limit=10)
            elif kpi_key in ["consommation_oxygene", "consommation_gaz", "poids_acier"]:
                col_map = {
                    "consommation_oxygene": ("BURNER_TOTALOXY", "Nm³"),
                    "consommation_gaz": ("BURNER_TOTALGAS", "Nm³"),
                    "poids_acier": ("TAPPING_WEIGHT", "kg"),
                }
                col, unite = col_map[kpi_key]
                return self.kpi_engine.execute_custom_sql(
                    f"SELECT ROUND(SUM({col}),2) as total, "
                    f"ROUND(AVG({col}),2) as moyenne, "
                    f"COUNT(*) as nb_coulees FROM EAF "
                    f"WHERE {col} IS NOT NULL"
                )
            else:
                return self.kpi_engine.get_arrets_by_type(limit=10)

        except Exception as e:
            logger.error("Erreur KPI", kpi=kpi_key, error=str(e))
            return {"error": str(e)}

    def _handle_free_sql(self, query: str) -> Dict[str, Any]:
        """Génère et exécute SQL libre via LLM."""
        try:
            messages = [
                SystemMessage(content="Tu es expert SQL SQLite pour une aciérie."),
                HumanMessage(content=SQL_AGENT_PROMPT.format(question=query)),
            ]
            response = self.llm.invoke(messages)
            sql = response.content.strip()

            # Nettoyer markdown si présent
            sql = re.sub(r'```sql|```', '', sql).strip()

            if not sql.upper().startswith("SELECT"):
                return {"error": "SQL non valide généré", "sql": sql}

            result = self.kpi_engine.execute_custom_sql(sql)
            result["generated_sql"] = sql
            return result

        except Exception as e:
            logger.error("Erreur SQL libre", error=str(e))
            return {"error": str(e)}

    def execute(self, state: AgentState) -> AgentState:
        """Nœud LangGraph : exécution SQL/KPI."""
        t_start = time.time()
        query = state["query"]

        logger.info("SQLAgent démarre", query=query[:80])

        # Détecter KPIs
        detected_kpis = detect_kpi(query)

        if detected_kpis:
            kpi_key = detected_kpis[0]
            logger.info("KPI détecté", kpi=kpi_key)
            result = self._handle_kpi(kpi_key, query)
            mode = "kpi_predefined"
        else:
            logger.info("Mode SQL libre")
            result = self._handle_free_sql(query)
            mode = "free_sql"

        latency = round((time.time() - t_start) * 1000, 2)

        # Formater résultat pour le contexte
        context = self._format_result(query, result, mode)

        return {
            **state,
            "retrieved_context": context,
            "tool_results": [result],
            "action_history": [{
                "agent": "sql_agent",
                "action": mode,
                "kpis_detected": detected_kpis,
                "latency_ms": latency,
            }],
            "metadata": {
                **state.get("metadata", {}),
                "sql_agent_latency_ms": latency,
                "mode": mode,
                "kpis_detected": detected_kpis,
            },
        }

    def _format_result(self, query: str, result: Dict, mode: str) -> str:
        """Formate le résultat KPI/SQL pour le LLM Generator."""
        if "error" in result:
            return f"Erreur : {result['error']}"

        lines = []

        if mode == "kpi_predefined":
            kpi_name = result.get("kpi", "KPI")
            lines.append(f"KPI : {kpi_name}")

            if "valeur" in result:
                lines.append(f"Valeur principale : {result['valeur']} {result.get('unite', '')}")

            if "details" in result:
                lines.append("Détails :")
                for k, v in result["details"].items():
                    k_clean = k.replace("_", " ").title()
                    lines.append(f"  - {k_clean} : {v}")

            if "valeur_totale_mwh" in result:
                lines.append(f"Total : {result['valeur_totale_mwh']} MWh")
                if "details" in result:
                    d = result["details"]
                    lines.append(f"  - EAF : {d.get('eaf_mwh', 0)} MWh")
                    lines.append(f"  - LF  : {d.get('lf_mwh', 0)} MWh")

            if "data" in result and result["data"]:
                lines.append(f"Données ({len(result['data'])} entrées) :")
                for row in result["data"][:8]:
                    row_str = " | ".join([f"{k}: {v}" for k, v in row.items()])
                    lines.append(f"  → {row_str}")

            if "total_coulees" in result:
                lines.append(f"Total coulées : {result['total_coulees']}")

        else:
            if "data" in result and result["data"]:
                lines.append(f"Résultats ({result.get('row_count', 0)} lignes) :")
                for row in result["data"][:8]:
                    row_str = " | ".join([f"{k}: {v}" for k, v in row.items()])
                    lines.append(f"  → {row_str}")
            elif "row_count" in result and result["row_count"] == 0:
                lines.append("Aucun résultat trouvé pour cette période.")

        return "\n".join(lines) if lines else "Aucune donnée disponible."