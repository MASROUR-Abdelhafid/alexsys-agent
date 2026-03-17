"""
Requêtes SQL pour les KPIs Aciérie.
Dialecte : SQLite
"""

from typing import Optional


def get_taux_disponibilite_query(
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
) -> str:
    """
    Taux de Disponibilité EAF.
    TD% = (Temps_Requis - Somme_Arrêts_Non_Techniques) / Temps_Requis * 100
    
    Exclus : Programmé + Technique (opérations normales)
    Inclus  : Incident, Mécanique, Électrique, Fonctionnel, Induit, Panne
    """
    date_filter = ""
    if date_debut and date_fin:
        date_filter = f"""
        AND DELAYSTART >= '{date_debut}'
        AND DELAYSTART <= '{date_fin}'"""

    return f"""
WITH arrets_programmes AS (
    SELECT COALESCE(SUM(DURATION), 0) AS total_programme
    FROM EAF_Arrets
    WHERE SECTIONNAME IN ('Programmé')
    {date_filter}
),
arrets_non_disponibilite AS (
    SELECT COALESCE(SUM(DURATION), 0) AS total_arrets
    FROM EAF_Arrets
    WHERE SECTIONNAME NOT IN ('Programmé', 'Technique', ' ')
    AND SECTIONNAME IS NOT NULL
    {date_filter}
),
periode AS (
    SELECT COUNT(DISTINCT DATE(DELAYSTART)) AS nb_jours
    FROM EAF_Arrets
    WHERE DELAYSTART IS NOT NULL
    {date_filter}
)
SELECT
    p.nb_jours,
    p.nb_jours * 24 * 3600                          AS temps_ouverture_sec,
    ap.total_programme                               AS arrets_programmes_sec,
    (p.nb_jours * 24 * 3600 - ap.total_programme)   AS temps_requis_sec,
    an.total_arrets                                  AS arrets_non_dispo_sec,
    ROUND(
        CAST(
            (p.nb_jours * 24 * 3600 - ap.total_programme - an.total_arrets)
            AS FLOAT
        ) / NULLIF(p.nb_jours * 24 * 3600 - ap.total_programme, 0) * 100,
        2
    ) AS taux_disponibilite_pct
FROM periode p, arrets_programmes ap, arrets_non_disponibilite an;
"""


def get_conso_electrique_query(
    groupby: str = "total",
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
    grade: Optional[str] = None,
) -> dict:
    """
    Consommation électrique EAF + LF.
    Retourne 2 requêtes séparées + instruction de fusion.
    """
    date_filter_eaf = ""
    date_filter_lf = ""
    grade_filter_eaf = ""
    grade_filter_lf = ""

    if date_debut and date_fin:
        date_filter_eaf = f"AND HEATDEPARTURE_ACT >= '{date_debut}' AND HEATDEPARTURE_ACT <= '{date_fin}'"
        date_filter_lf = f"AND HEATDEPARTURE_ACT >= '{date_debut}' AND HEATDEPARTURE_ACT <= '{date_fin}'"

    if grade:
        grade_filter_eaf = f"AND STEELGRADECODE_ACT = '{grade}'"
        grade_filter_lf = f"AND STEELGRADECODE_ACT = '{grade}'"

    if groupby == "jour":
        group_col_eaf = "DATE(HEATDEPARTURE_ACT) AS periode"
        group_col_lf = "DATE(HEATDEPARTURE_ACT) AS periode"
        group_by_clause = "GROUP BY DATE(HEATDEPARTURE_ACT)"
    elif groupby == "semaine":
        group_col_eaf = "strftime('%Y-W%W', HEATDEPARTURE_ACT) AS periode"
        group_col_lf = "strftime('%Y-W%W', HEATDEPARTURE_ACT) AS periode"
        group_by_clause = "GROUP BY strftime('%Y-W%W', HEATDEPARTURE_ACT)"
    elif groupby == "mois":
        group_col_eaf = "strftime('%Y-%m', HEATDEPARTURE_ACT) AS periode"
        group_col_lf = "strftime('%Y-%m', HEATDEPARTURE_ACT) AS periode"
        group_by_clause = "GROUP BY strftime('%Y-%m', HEATDEPARTURE_ACT)"
    elif groupby == "grade":
        group_col_eaf = "STEELGRADECODE_ACT AS periode"
        group_col_lf = "STEELGRADECODE_ACT AS periode"
        group_by_clause = "GROUP BY STEELGRADECODE_ACT"
    else:
        group_col_eaf = "'Total' AS periode"
        group_col_lf = "'Total' AS periode"
        group_by_clause = ""

    query_eaf = f"""
SELECT {group_col_eaf},
       COALESCE(SUM(TOTAL_ELEC_EGY), 0) AS conso_eaf_wh
FROM EAF
WHERE TOTAL_ELEC_EGY IS NOT NULL
{date_filter_eaf}
{grade_filter_eaf}
{group_by_clause}
ORDER BY periode;
"""

    query_lf = f"""
SELECT {group_col_lf},
       COALESCE(SUM(ELEC_CONS_TOTAL), 0) AS conso_lf_wh
FROM LF
WHERE ELEC_CONS_TOTAL IS NOT NULL
{date_filter_lf}
{grade_filter_lf}
{group_by_clause}
ORDER BY periode;
"""

    return {
        "query_eaf": query_eaf,
        "query_lf": query_lf,
        "groupby": groupby,
    }


def get_production_coulees_query(
    groupby: str = "total",
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
) -> str:
    date_filter = ""
    if date_debut and date_fin:
        date_filter = f"AND HEATDEPARTURE_ACT >= '{date_debut}' AND HEATDEPARTURE_ACT <= '{date_fin}'"

    if groupby == "jour":
        group_col = "DATE(HEATDEPARTURE_ACT) AS periode"
        group_by = "GROUP BY DATE(HEATDEPARTURE_ACT)"
    elif groupby == "mois":
        group_col = "strftime('%Y-%m', HEATDEPARTURE_ACT) AS periode"
        group_by = "GROUP BY strftime('%Y-%m', HEATDEPARTURE_ACT)"
    else:
        group_col = "'Total' AS periode"
        group_by = ""

    return f"""
SELECT {group_col},
       COUNT(DISTINCT HEATID) AS nb_coulees,
       ROUND(SUM(TAPPING_WEIGHT) / 1000.0, 2) AS tonnage_total_t
FROM EAF
WHERE TAPPING_WEIGHT IS NOT NULL
{date_filter}
{group_by}
ORDER BY periode;
"""


def get_defauts_brames_query(
    gravite: Optional[int] = None,
    limit: int = 10,
) -> str:
    gravite_filter = ""
    if gravite is not None:
        gravite_filter = f"AND DFB_GRAVITE = {gravite}"

    return f"""
SELECT
    DFT_NOM AS type_defaut,
    DFB_GRAVITE AS gravite,
    COUNT(*) AS nb_defauts,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS pct_total
FROM Defauts_Brame
WHERE 1=1
{gravite_filter}
GROUP BY DFT_NOM, DFB_GRAVITE
ORDER BY nb_defauts DESC
LIMIT {limit};
"""


def get_arrets_by_type_query(limit: int = 10) -> str:
    return f"""
SELECT
    GROUPNAME AS type_arret,
    SECTIONNAME AS categorie,
    COUNT(*) AS nb_arrets,
    ROUND(SUM(DURATION) / 3600.0, 2) AS duree_totale_heures,
    ROUND(AVG(DURATION) / 60.0, 2) AS duree_moyenne_min
FROM EAF_Arrets
WHERE GROUPNAME IS NOT NULL
GROUP BY GROUPNAME, SECTIONNAME
ORDER BY duree_totale_heures DESC
LIMIT {limit};
"""