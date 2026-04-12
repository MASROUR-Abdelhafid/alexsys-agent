```markdown
# Guide Utilisateur — Assistant KPI Aciérie Maghreb Steel

## Démarrage rapide

### 1. Lancer le système
```cmd
cd C:\Users\bassi\Desktop\pfe\alexsys-agent
docker-compose -f docker/docker-compose.yml up -d
python scripts/start_api.py
```

### 2. Ouvrir l'interface
Ouvrir `frontend/index.html` dans votre navigateur.

### 3. Dashboard KPI
Ouvrir `frontend/dashboard.html` pour le tableau de bord.

---

## Types de questions

### Questions KPI (données officielles Gold)
- "Quel est le taux de disponibilité EAF ?"
- "Quelle est la consommation électrique totale ?"
- "Combien de coulées ont été produites ?"
- "Quelle est la consommation d'oxygène EAF ?"
- "Quel est le poids moyen des brames ?"

### Questions documentaires (RAG)
- "Comment fonctionne le four EAF ?"
- "Quel est le rôle du four LF ?"
- "Comment fonctionne la coulée continue CCM ?"
- "Qu'est-ce que le PAF ?"

### Questions temporelles
- "Quelle est la consommation électrique par mois ?"
- "Quelle est la consommation électrique par grade ?"

---

## Architecture technique

```
Question utilisateur
        ↓
    Planner LangGraph
    (KPI / DOC / Direct)
        ↓
    ┌───┴────┐
    ▼        ▼
SQLAgent    RetrieverAgent
(KPI Gold)  (RAG Milvus)
    ↓        ↓
KPIEngine   Hybrid Search
(SQLite)    BM25 + Dense
            Cross-Encoder
    └───┬────┘
        ▼
   Generator LLM
   (Groq Llama 3.1)
        ↓
   Réponse finale
```

---

## Indicateurs KPI disponibles

| KPI | Description | Unité |
|-----|-------------|-------|
| Taux de disponibilité EAF | TD% = (Temps_Requis - Arrêts) / Temps_Requis | % |
| Consommation électrique | EAF + LF | MWh |
| Production coulées | Nombre et tonnage | coulées / t |
| Défauts brames | Par type et gravité | count |
| Consommation oxygène | Four EAF | Nm³ |
| Poids brames | Moyen / total / min / max | kg / t |
| Arrêts EAF | Par type et durée | heures |

---

## Ajout de nouveaux documents (back-office)

1. Placer le PDF dans `data/acierie/`
2. Relancer l'indexation :
```cmd
python scripts/index_documents.py
```

---

## Support

Projet PFE — Master Machine Learning Avancé  
Encadrant : Alexsys Solutions
```