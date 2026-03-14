"""
Moteur KPI Aciérie.
Exécute les requêtes et retourne les résultats formatés.
"""

import sqlite3
import pandas as pd
from typing import Dict, Any, Optional
import structlog

from kpi.queries import (
    get_taux_disponibilite_query,
    get_conso_electrique_query,
    get_production_coulees_query,
    get_defauts_brames_query,
    get_arrets_by_type_query,
)

logger = structlog.get_logger(__name__)

DB_PATH = "data/acierie.db"


class KPIEngine:
    """Moteur d'exécution des KPIs Aciérie."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        logger.info("KPIEngine initialisé", db=db_path)

    def _execute(self, sql: str) -> pd.DataFrame:
        """Exécute une requête SQL et retourne un DataFrame."""
        conn = sqlite3.connect(self.db_path)
        try:
            df = pd.read_sql_query(sql, conn)
            return df
        finally:
            conn.close()

    def _execute_two(self, sql1: str, sql2: str) -> tuple:
        """Exécute deux requêtes séparément."""
        conn = sqlite3.connect(self.db_path)
        try:
            df1 = pd.read_sql_query(sql1, conn)
            df2 = pd.read_sql_query(sql2, conn)
            return df1, df2
        finally:
            conn.close()

    def get_taux_disponibilite(
        self,
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calcule le Taux de Disponibilité EAF."""
        sql = get_taux_disponibilite_query(date_debut, date_fin)
        df = self._execute(sql)

        if df.empty:
            return {"error": "Aucune donnée disponible"}

        row = df.iloc[0]
        return {
            "kpi": "Taux de Disponibilité EAF",
            "valeur": float(row.get("taux_disponibilite_pct", 0)),
            "unite": "%",
            "details": {
                "nb_jours": int(row.get("nb_jours", 0)),
                "temps_requis_heures": round(float(row.get("temps_requis_sec", 0)) / 3600, 2),
                "tous_arrets_heures": round(float(row.get("tous_arrets_sec", 0)) / 3600, 2),
                "arrets_programmes_heures": round(float(row.get("arrets_programmes_sec", 0)) / 3600, 2),
            },
        }

    def get_consommation_electrique(
        self,
        groupby: str = "total",
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None,
        grade: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calcule la consommation électrique EAF + LF."""
        queries = get_conso_electrique_query(groupby, date_debut, date_fin, grade)
        df_eaf, df_lf = self._execute_two(
            queries["query_eaf"],
            queries["query_lf"],
        )

        # Fusion des deux résultats
        if groupby == "total":
            conso_eaf = float(df_eaf["conso_eaf_wh"].sum()) if not df_eaf.empty else 0
            conso_lf = float(df_lf["conso_lf_wh"].sum()) if not df_lf.empty else 0
            total = conso_eaf + conso_lf

            return {
                "kpi": "Consommation Électrique",
                "valeur_totale_wh": total,
                "valeur_totale_mwh": round(total / 1_000_000, 2),
                "details": {
                    "eaf_wh": conso_eaf,
                    "lf_wh": conso_lf,
                    "eaf_mwh": round(conso_eaf / 1_000_000, 2),
                    "lf_mwh": round(conso_lf / 1_000_000, 2),
                },
                "groupby": groupby,
            }
        else:
            # Merge par période
            merged = pd.merge(df_eaf, df_lf, on="periode", how="outer").fillna(0)
            merged["conso_totale_wh"] = merged["conso_eaf_wh"] + merged["conso_lf_wh"]
            merged["conso_totale_mwh"] = (merged["conso_totale_wh"] / 1_000_000).round(2)

            return {
                "kpi": "Consommation Électrique",
                "groupby": groupby,
                "data": merged.to_dict(orient="records"),
                "total_wh": float(merged["conso_totale_wh"].sum()),
                "total_mwh": round(float(merged["conso_totale_wh"].sum()) / 1_000_000, 2),
            }

    def get_production_coulees(
        self,
        groupby: str = "total",
        date_debut: Optional[str] = None,
        date_fin: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calcule la production en nombre de coulées."""
        sql = get_production_coulees_query(groupby, date_debut, date_fin)
        df = self._execute(sql)
        return {
            "kpi": "Production Coulées",
            "groupby": groupby,
            "data": df.to_dict(orient="records"),
            "total_coulees": int(df["nb_coulees"].sum()) if not df.empty else 0,
        }

    def get_defauts_brames(
        self,
        gravite: Optional[int] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Analyse des défauts brames."""
        sql = get_defauts_brames_query(gravite, limit)
        df = self._execute(sql)
        return {
            "kpi": "Défauts Brames",
            "data": df.to_dict(orient="records"),
            "total_defauts": int(df["nb_defauts"].sum()) if not df.empty else 0,
        }

    def get_arrets_by_type(self, limit: int = 10) -> Dict[str, Any]:
        """Analyse des arrêts par type."""
        sql = get_arrets_by_type_query(limit)
        df = self._execute(sql)
        return {
            "kpi": "Arrêts par Type",
            "data": df.to_dict(orient="records"),
        }

    def execute_custom_sql(self, sql: str) -> Dict[str, Any]:
        """Exécute une requête SQL personnalisée (SELECT uniquement)."""
        if not sql.strip().upper().startswith("SELECT"):
            return {"error": "Seules les requêtes SELECT sont autorisées"}
        try:
            df = self._execute(sql)
            return {
                "data": df.to_dict(orient="records"),
                "columns": list(df.columns),
                "row_count": len(df),
            }
        except Exception as e:
            return {"error": str(e)}