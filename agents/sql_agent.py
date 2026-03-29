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
                    params.get("date_debut"), params.get("date_fin"),
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

            elif kpi_key == "consommation_oxygene":
                return self.kpi_engine.get_consommation_oxygene()

            elif kpi_key == "production_brames":
                return self.kpi_engine.get_poids_brames()

            elif kpi_key == "poids_acier":
                return self.kpi_engine.execute_custom_sql(
                    "SELECT ROUND(SUM(TAPPING_WEIGHT)/1000.0,2) as total_t, "
                    "ROUND(AVG(TAPPING_WEIGHT)/1000.0,2) as moy_t, "
                    "COUNT(*) as nb FROM EAF WHERE TAPPING_WEIGHT > 0"
                )
            elif kpi_key == "consommation_gaz":
                return self.kpi_engine.execute_custom_sql(
                    "SELECT ROUND(SUM(BURNER_TOTALGAS),2) as total_gaz_nm3, "
                    "ROUND(AVG(BURNER_TOTALGAS),2) as moy_par_coulee, "
                    "COUNT(*) as nb_coulees FROM EAF WHERE BURNER_TOTALGAS > 0"
                )
            elif kpi_key == "duree_tap_to_tap":
                return self.kpi_engine.execute_custom_sql(
                    "SELECT ROUND(AVG((strftime('%s',HEATDEPARTURE_ACT)"
                    "-strftime('%s',HEATANNOUNCE_ACT))/60.0),2) as duree_moy_min, "
                    "COUNT(*) as nb FROM EAF WHERE HEATANNOUNCE_ACT IS NOT NULL "
                    "AND HEATDEPARTURE_ACT IS NOT NULL"
                )
            elif kpi_key == "ferraille_chargee":
                return self.kpi_engine.execute_custom_sql(
                    "SELECT CAT_NOM, ROUND(SUM(CSD_POIDS),2) as total_kg, "
                    "COUNT(*) as nb FROM PAF WHERE CSD_POIDS > 0 "
                    "GROUP BY CAT_NOM ORDER BY total_kg DESC LIMIT 10"
                )
            else:
                return self.kpi_engine.get_arrets_by_type(limit=10)

        except Exception as e:
            logger.error("Erreur KPI", kpi=kpi_key, error=str(e))
            return {"error": str(e)}
        
    def _handle_free_sql(self, query: str) -> Dict[str, Any]:
        """Génère et exécute SQL libre via LLM."""
        try:
            safe_query = query.replace("{", "").replace("}", "")
            prompt = SQL_AGENT_PROMPT.replace("{question}", safe_query)

            messages = [
                SystemMessage(content="Tu es expert SQL SQLite pour une aciérie."),
                HumanMessage(content=prompt),
            ]

            response = self.llm.invoke(messages)
            sql = response.content.strip()

            sql = re.sub(r'```sql|```', '', sql).strip()

            if not sql.upper().startswith("SELECT"):
                return {"error": "SQL non valide généré", "sql": sql}

            if ";" in sql.strip()[:-1]:
                return {"error": "Requête multiple interdite", "sql": sql}

            result = self.kpi_engine.execute_custom_sql(sql)

            if "error" not in result:
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

        context = self._format_result(query, result, mode)

        return {
            **state,
            "retrieved_context": context,
            "tool_results": [result],
            "action_history": state.get("action_history", []) + [{
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

        if "data" in result:
            if result["data"]:
                lines.append(f"Données par période :")
                for row in result["data"][:12]:
                    periode = row.get("periode", "")
                    total_mwh = round(row.get("conso_totale_wh", 0) / 1_000_000, 3)
                    eaf_mwh = round(row.get("conso_eaf_wh", 0) / 1_000_000, 3)
                    lf_mwh = round(row.get("conso_lf_wh", 0) / 1_000_000, 3)
                    lines.append(f"  → {periode} : Total={total_mwh} MWh (EAF={eaf_mwh}, LF={lf_mwh})")

                if "total_coulees" in result:
                    lines.append(f"Total coulées : {result['total_coulees']}")
            else:
                lines.append("Aucun résultat trouvé pour cette période.")

        return "\n".join(lines) if lines else "Aucune donnée disponible."