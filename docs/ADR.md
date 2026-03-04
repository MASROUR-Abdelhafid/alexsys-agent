# Architecture Decision Records (ADR)
## Projet : RAG Multi-Agentique — Alexsys Solutions

---

## ADR-001 : Choix du Framework d'Orchestration → LangGraph

### Contexte
Besoin d'un graphe cyclique pour l'orchestration agentique.

### Décision
**LangGraph** retenu vs CrewAI.

### Justification
| Critère | LangGraph | CrewAI |
|---|---|---|
| Graphe cyclique natif | ✅ | ❌ (séquentiel) |
| Contrôle flux granulaire | ✅ Total | ⚠️ Limité |
| Intégration LangChain | ✅ Native | ⚠️ Partielle |
| Debugging/Observabilité | ✅ LangSmith | ❌ |
| Maturité industrielle | ✅ | ⚠️ Jeune |

---

## ADR-002 : Choix Vector DB → Milvus

### Contexte
Stockage et recherche vectorielle pour le RAG.

### Décision
**Milvus** retenu vs Pinecone/Weaviate.

### Justification
| Critère | Milvus | Pinecone | Weaviate |
|---|---|---|---|
| Self-hosted | ✅ | ❌ Cloud only | ✅ |
| Coût | Gratuit | Payant | Gratuit |
| Performance | ✅ HNSW | ✅ | ✅ |
| Docker natif | ✅ | ❌ | ✅ |
| Hybrid search | ✅ | ⚠️ | ✅ |
| Données sensibles | ✅ On-premise | ❌ | ✅ |

---

## ADR-003 : Choix LLM → GPT-4o (+ Llama 3.1 fallback)

### Décision
**GPT-4o** via API OpenAI en primaire, **Llama 3.1** via Ollama en local.

### Justification
- GPT-4o : meilleure performance function calling, benchmark MMLU supérieur
- Llama 3.1 : fallback offline, données sensibles, coût zéro
- Architecture abstraite via LangChain → swap transparent

---

## ADR-004 : Hybrid Search → RRF Fusion

### Décision
**Reciprocal Rank Fusion (RRF)** pour combiner Dense + Sparse.

### Justification
RRF (Cormack et al., 2009) est robuste sans hyperparamètre critique :

score_rrf(d) = Σ 1/(k + rank_i(d))  [k=60 par défaut]

Supérieur à la fusion par score brut car invariant aux distributions de scores.

---

## ADR-005 : Re-ranking → Cross-Encoder

### Décision
**ms-marco-MiniLM-L-6-v2** (sentence-transformers).

### Justification
- Cross-encoder : attend la paire (query, document) → scoring joint plus précis
- Bi-encoder (embeddings) : rapide mais approximatif
- Pipeline : Bi-encoder pour recall large → Cross-encoder pour precision finale

---

## ADR-006 : Backend → FastAPI

### Justification
- ASGI async natif → performances I/O non-bloquantes
- Validation automatique Pydantic
- OpenAPI/Swagger auto-généré
- Standard industrie MLOps

---

## ADR-007 : Monitoring → MLflow + Prometheus

### Décision
MLflow pour tracking expériences + métriques custom en logs structurés.

### Justification
- MLflow : standard MLOps, UI intégrée, comparaison runs
- Structlog : logs JSON machine-readable pour analyse
- Prometheus : métriques temps-réel (latence p95, p99)