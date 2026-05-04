# 🏭 Chatbot KPI IA — Aciérie Maghreb Steel

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.112-green)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange)
![Benchmark](https://img.shields.io/badge/Benchmark-10%2F10-brightgreen)
![Accuracy](https://img.shields.io/badge/Accuracy-100%25-brightgreen)
![F1](https://img.shields.io/badge/F1--Score-100%25-brightgreen)
![CDC](https://img.shields.io/badge/Conformit%C3%A9%20CDC-21%2F21-brightgreen)

**Projet PFE — Master Machine Learning Avancé**  
Encadrant industriel : **Alexsys Solutions** | Site : **Aciérie Maghreb Steel**

</div>

---

## 📋 Description

Système multi-agents RAG permettant un accès **automatisé, structuré et en temps réel** aux indicateurs de performance industrielle (KPI) de l'Aciérie Maghreb Steel via un chatbot IA en langage naturel.

Le système répond à deux types de questions :
- **KPI Gold** : indicateurs officiels calculés depuis la base de données réelle de l'usine
- **Documentation RAG** : questions sur les procédés techniques (EAF, LF, CCM, PAF)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERFACE UTILISATEUR                     │
│              Chat UI · Dashboard · Export BI                 │
└─────────────────────────┬───────────────────────────────────┘
                          │ FastAPI REST
┌─────────────────────────▼───────────────────────────────────┐
│                   ORCHESTRATEUR LANGGRAPH                    │
│                    PlannerAgent (LLaMA 3.1)                  │
│              ┌───────────┴───────────┐                       │
│         KPI Gold                  RAG DOC                    │
│        SQLAgent                RetrieverAgent                │
│       (SQLite)          Dense+BM25+RRF+CrossEncoder          │
│           │                    (Milvus)                       │
│           └───────────┬───────────┘                          │
│                  GeneratorAgent                              │
│               (Groq LLaMA 3.1 8B)                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Résultats

| Métrique | Valeur |
|---|---|
| **Accuracy globale** | **100% (12/12)** |
| **F1-Score KPI** | **100%** |
| **Précision KPI** | **100%** |
| **Rappel KPI** | **100%** |
| **Benchmark** | **10/10 = 100%** |
| **Latence KPI** | **~342ms** |
| **Latence RAG** | **~5747ms** |
| **Latence Direct** | **~3ms** |
| **Conformité CDC** | **21/21 axes** |
| **Hallucination KPI** | **0%** |

---

## 🛠️ Stack technique

| Composant | Technologie | Version |
|---|---|---|
| LLM | Groq — LLaMA 3.1 8B Instant | latest |
| Orchestration | LangGraph | 0.2 |
| Vector DB | Milvus HNSW COSINE | 2.4 |
| Embeddings | all-MiniLM-L6-v2 | sentence-transformers |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 | — |
| Sparse | BM25Okapi (k1=1.5, b=0.75) | rank-bm25 |
| Base de données | SQLite | 3.45 |
| API | FastAPI | 0.112 |
| Infra | Docker + Milvus Standalone | — |

---

## 📦 Installation

### Prérequis
- Python 3.11+
- Docker Desktop
- Clé API Groq (gratuit sur https://console.groq.com)

### 1. Cloner le projet

```bash
git clone https://github.com/MASROUR-Abdelhafid/alexsys-agent.git
cd alexsys-agent
```

### 2. Créer l'environnement virtuel

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

```bash
cp .env.example .env
# Éditer .env avec vos clés API
```

### 5. Lancer Milvus (Docker)

```bash
cd docker
docker-compose up -d
cd ..
```

### 6. Initialiser la base de données

```bash
python scripts/init_database.py
```

### 7. Indexer la documentation

```bash
python scripts/index_documents.py
```

### 8. Lancer l'API

```bash
python scripts/start_api.py
```

### 9. Ouvrir l'interface

```
frontend/index.html     → Chat KPI
frontend/dashboard.html → Dashboard métriques
```

---

## 🚀 Utilisation rapide

```bash
# Vérification santé API
curl http://localhost:8000/api/v1/health

# Liste des KPIs disponibles
curl http://localhost:8000/api/v1/kpis \
  -H "Authorization: Bearer maghreb_readonly_2025"

# Export CSV pour BI
curl http://localhost:8000/api/v1/export/kpis \
  -H "Authorization: Bearer maghreb_readonly_2025" \
  -o kpis_export.csv

# Stats admin
curl http://localhost:8000/api/v1/admin/stats \
  -H "Authorization: Bearer maghreb_admin_2025"
```

---

## 📈 KPIs disponibles

| KPI | Formule | Unité |
|---|---|---|
| Taux de Disponibilité EAF | (TR - Arrêts) / TR × 100 | % |
| Consommation Électrique | Σ EAF + Σ LF | MWh |
| Production Coulées | COUNT coulées | coulées |
| Défauts Brames | COUNT + TOP défauts | défauts |
| Consommation Oxygène | Σ BURNER_TOTALOXY | Nm³ |
| Poids Moyen Brames | AVG PIECE_WEIGHT_MEAS | kg |
| Consommation GPL | Σ BURNER_TOTALGAS | Nm³ |
| Tap-to-tap | AVG durée EAF | min |
| Ferraille chargée | Σ CSD_POIDS | tonnes |
| Arrêts par type | SUM DURATION GROUP BY | heures |

---

## 🔐 Sécurité (RBAC)

| Rôle | Token | Accès |
|---|---|---|
| Admin | `maghreb_admin_2025` | Tous endpoints + stats |
| Opérateur | `maghreb_steel_2025` | Chat + KPIs + Export |
| Lecteur | `maghreb_readonly_2025` | KPIs + Health |

---

## 📁 Structure du projet

```
alexsys-agent/
├── agents/
│   ├── state.py          # AgentState LangGraph
│   ├── planner.py        # Routage kpi/doc/direct
│   ├── sql_agent.py      # KPI Engine SQL
│   ├── retriever.py      # RAG Pipeline
│   ├── generator.py      # Génération réponse
│   └── graph.py          # LangGraph DAG
├── kpi/
│   ├── definitions.py    # 10 KPIs Gold
│   ├── engine.py         # Moteur de calcul
│   └── queries.py        # Requêtes SQL
├── rag/
│   ├── ingestion.py      # Chunking PDF/TXT
│   ├── vector_store.py   # Milvus HNSW
│   ├── sparse_retrieval.py # BM25
│   ├── embeddings.py     # all-MiniLM-L6-v2
│   └── reranker.py       # Cross-Encoder
├── api/
│   ├── routes.py         # 8 endpoints FastAPI
│   ├── schemas.py        # Pydantic schemas
│   └── main.py           # App FastAPI
├── frontend/
│   ├── index.html        # Chat UI
│   └── dashboard.html    # Dashboard KPI
├── scripts/
│   ├── init_database.py  # Import Excel → SQLite
│   ├── index_documents.py # Indexation Milvus
│   ├── benchmark.py      # Tests 10/10
│   ├── evaluation.py     # Métriques F1/Précision
│   ├── view_audit.py     # Stats audit trail
│   └── start_api.py      # Démarrage API
├── data/
│   ├── acierie/          # PDF + schémas
│   └── benchmark_results.json
├── docker/
│   └── docker-compose.yml
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🧪 Tests

```bash
# Benchmark 10/10
python scripts/benchmark.py

# Évaluation complète F1/Précision/Rappel
python scripts/evaluation.py

# Audit trail
python scripts/view_audit.py
```

---

## 📡 API Endpoints

| Méthode | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/v1/chat` | Chatbot KPI + RAG | Opérateur |
| GET | `/api/v1/health` | Santé API | Public |
| GET | `/api/v1/kpis` | Liste KPIs Gold | Lecteur |
| GET | `/api/v1/dashboard` | Données dashboard | Lecteur |
| GET | `/api/v1/export/kpis` | Export CSV BI | Lecteur |
| POST | `/api/v1/upload-document` | Indexer document | Opérateur |
| POST | `/api/v1/feedback` | Feedback 👍/👎 | Opérateur |
| GET | `/api/v1/admin/stats` | Stats usage | Admin |

---

## 👤 Auteur

**MASROUR Abdelhafid**  
Master Machine Learning Avancé  
Projet PFE encadré par **Alexsys Solutions**  
Site industriel : **Aciérie Maghreb Steel**

---

## 📄 Licence

Projet académique — Usage interne uniquement.