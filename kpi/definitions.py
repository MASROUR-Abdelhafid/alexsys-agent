"""
Définitions des KPIs Aciérie.
Source : Dictionnaire de données + Instructions de calcul.
"""

KPI_DEFINITIONS = {
    "taux_disponibilite": {
        "nom": "Taux de Disponibilité (TD%)",
        "description": "Mesure le temps effectif de production vs temps requis",
        "unite": "%",
        "formule": "(Temps_Requis - Somme_Arrêts) / Temps_Requis × 100",
        "table": "EAF_Arrets",
        "mots_cles": [
            "disponibilité", "disponibilite", "td", "arrêt", "arret",
            "uptime", "downtime", "panne", "maintenance"
        ],
    },
    "consommation_electrique": {
        "nom": "Consommation Électrique (Wh)",
        "description": "Somme consommation EAF + LF",
        "unite": "Wh",
        "formule": "SUM(EAF.TOTAL_ELEC_EGY) + SUM(LF.ELEC_CONS_TOTAL)",
        "tables": ["EAF", "LF"],
        "mots_cles": [
            "électrique", "electrique", "énergie", "energie",
            "consommation", "kwh", "wh", "conso elec"
        ],
    },
    "production_coulees": {
        "nom": "Production — Nombre de Coulées",
        "description": "Nombre total de coulées produites",
        "unite": "coulées",
        "table": "EAF",
        "mots_cles": [
            "coulée", "coulee", "production", "nombre coulées",
            "heat", "heatid"
        ],
    },
    "production_brames": {
        "nom": "Production — Brames",
        "description": "Nombre et poids total des brames produites",
        "unite": "brames / tonnes",
        "table": "CCM_Brame",
        "mots_cles": [
            "brame", "slab", "poids brame", "production brame",
            "ccm", "coulée continue"
        ],
    },
    "defauts_brames": {
        "nom": "Défauts Brames",
        "description": "Analyse des défauts par gravité et type",
        "unite": "count",
        "table": "Defauts_Brame",
        "mots_cles": [
            "défaut", "defaut", "qualité", "qualite", "gravité",
            "gravite", "brame defaut", "rebut"
        ],
    },
    "consommation_oxygene": {
        "nom": "Consommation Oxygène EAF",
        "description": "Total oxygène consommé au four EAF",
        "unite": "Nm³",
        "table": "EAF",
        "mots_cles": [
            "oxygène", "oxygene", "o2", "burner", "oxy"
        ],
    },
    "consommation_gaz": {
        "nom": "Consommation GPL/Gaz EAF",
        "description": "Total gaz consommé au four EAF",
        "unite": "Nm³",
        "table": "EAF",
        "mots_cles": [
            "gaz", "gpl", "gas", "brûleur", "bruleur"
        ],
    },
    "poids_acier": {
        "nom": "Poids Acier Produit (Tapping)",
        "description": "Poids total acier produit à la vidange EAF",
        "unite": "tonnes",
        "table": "EAF",
        "mots_cles": [
            "tapping", "vidange", "poids acier", "tonnage"
        ],
    },
    "duree_tap_to_tap": {
        "nom": "Durée Tap-to-Tap EAF",
        "description": "Durée moyenne entre deux vidanges EAF",
        "unite": "minutes",
        "table": "EAF",
        "mots_cles": [
            "tap to tap", "tap-to-tap", "durée coulée", "cycle"
        ],
    },
    "ferraille_chargee": {
        "nom": "Ferraille Chargée PAF",
        "description": "Poids total ferraille chargée par catégorie",
        "unite": "tonnes",
        "table": "PAF",
        "mots_cles": [
            "ferraille", "panier", "paf", "charge", "scrap",
            "catégorie ferraille"
        ],
    },
}


def detect_kpi(query: str) -> list:
    """
    Détecte les KPIs pertinents dans une query.
    Priorité : defauts_brames avant production_brames.
    """
    query_lower = query.lower()
    detected = []

    # Priorité explicite défauts
    defaut_keywords = ["défaut", "defaut", "qualité", "qualite",
                       "gravité", "gravite", "rebut", "frequents", "fréquents"]
    if any(k in query_lower for k in defaut_keywords):
        detected.append("defauts_brames")

    for kpi_key, kpi_data in KPI_DEFINITIONS.items():
        if kpi_key == "defauts_brames":
            continue  # Déjà traité
        for mot in kpi_data["mots_cles"]:
            if mot in query_lower:
                if kpi_key not in detected:
                    detected.append(kpi_key)
                break

    return detected


def is_kpi_query(query: str) -> bool:
    """Détermine si la query concerne un KPI."""
    return len(detect_kpi(query)) > 0


def is_doc_query(query: str) -> bool:
    """Détermine si la query concerne la documentation technique."""
    doc_keywords = [
        "comment", "pourquoi", "qu'est-ce", "définition",
        "procédé", "process", "fonctionnement", "description",
        "expliquer", "c'est quoi", "présentation", "etape",
        "eaf", "lf", "ccm", "paf", "four", "fusion",
    ]
    query_lower = query.lower()
    return any(kw in query_lower for kw in doc_keywords)