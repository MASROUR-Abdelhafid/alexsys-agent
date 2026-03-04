# Architecture du Système RAG Multi-Agentique — Alexsys Solutions

## Schéma Global

​```mermaid
graph TD
    U([👤 Utilisateur]) -->|Requête| API[🌐 FastAPI REST]
    API --> ORCH[🧠 Orchestrateur LangGraph]

    ORCH --> PLAN[📋 Agent Planner]
    PLAN -->|Plan d'actions| ORCH

    ORCH --> RET[🔍 Agent Retriever]
    RET --> HS[Hybrid Search]
    HS --> DENSE[Dense: Embeddings\nMilvus]
    HS --> SPARSE[Sparse: BM25]
    DENSE --> FUSE[Score Fusion RRF]
    SPARSE --> FUSE
    FUSE --> RERANK[Cross-Encoder Re-ranking]
    RERANK -->|Chunks pertinents| ORCH

    ORCH --> TOOL[🛠 Agent Tool Executor]
    TOOL --> API_T[API externe simulée]
    TOOL --> DB[Base de données SQLite]
    TOOL --> CRM[CRM Mock]
    TOOL --> PDF[Générateur PDF]

    ORCH --> MEM[🧠 Memory]
    MEM --> STM[Short-term: Buffer]
    MEM --> LTM[Long-term: Milvus]

    ORCH -->|Réponse finale| LLM[LLM GPT-4o / Llama 3.1]
    LLM --> API
    API --> U

    ORCH --> MON[📊 Monitoring]
    MON --> MLF[MLflow]
    MON --> LOG[Structured Logs]
    MON --> MET[Métriques: latence/coût/hallucination]
​```

## Flux de Traitement

​```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant API as FastAPI
    participant P as Planner
    participant R as Retriever
    participant T as Tool Executor
    participant L as LLM

    U->>API: POST /query {"question": "..."}
    API->>P: Analyser la requête
    P->>P: Décomposer en sous-tâches
    P->>R: Sous-tâche retrieval
    R->>R: Hybrid Search + Rerank
    R->>P: Top-K chunks
    P->>T: Sous-tâche tool (si besoin)
    T->>T: Appel API/BDD/CRM
    T->>P: Résultat outil
    P->>L: Contexte enrichi + question
    L->>API: Réponse générée
    API->>U: JSON response + metadata
​```