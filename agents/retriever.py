"""
Agent Retriever — RAG Pipeline Aciérie.
Hybrid Search + Cross-Encoder sur documentation technique.
"""

import time
from typing import Dict, Any
import structlog

from agents.state import AgentState
from rag.vector_store import MilvusVectorStore
from rag.sparse_retrieval import BM25Retriever
from rag.ingestion import DocumentIngestionPipeline, IngestionConfig
from rag.reranker import CrossEncoderReranker

logger = structlog.get_logger(__name__)


class RetrieverAgent:
    """
    Agent Retriever — Recherche dans la documentation aciérie.

    Pipeline :
    1. Dense search  → Milvus HNSW (sémantique)
    2. BM25 search   → Sparse (lexical)
    3. Fusion RRF    → Combinaison scores
    4. Reranking     → Cross-Encoder précision
    5. Contexte      → Formatage avec citations
    """

    _initialized = False
    _vector_store = None
    _bm25 = None
    _reranker = None
    _chunks = None

    def __init__(self, top_k: int = 5):
        self.top_k = top_k
        if not RetrieverAgent._initialized:
            self._setup()

    def _setup(self):
        """Initialise les composants RAG (singleton)."""
        logger.info("Initialisation RetrieverAgent RAG...")

        try:
            # Vector store
            RetrieverAgent._vector_store = MilvusVectorStore()

            # Vérifier que la collection est peuplée
            stats = RetrieverAgent._vector_store.get_collection_stats()
            if stats.get("num_entities", 0) == 0:
                logger.warning("Collection Milvus vide — indexation nécessaire")
                RetrieverAgent._initialized = False
                return

            # BM25 — réindexer les chunks depuis le PDF
            config = IngestionConfig(chunk_size=600, chunk_overlap=80)
            pipeline = DocumentIngestionPipeline(config)

            import os
            pdf_path = "data/acierie/Description_du_processus_acierie.pdf"
            if not os.path.exists(pdf_path):
                pdf_path = "data/acierie/Description_du_processus_aciérie.pdf"

            if os.path.exists(pdf_path):
                RetrieverAgent._chunks = pipeline.ingest(pdf_path)
                bm25 = BM25Retriever()
                bm25.index(RetrieverAgent._chunks)
                RetrieverAgent._bm25 = bm25
                logger.info("BM25 indexé", docs=len(RetrieverAgent._chunks))
            else:
                logger.warning("PDF aciérie introuvable pour BM25")

            # Cross-Encoder
            RetrieverAgent._reranker = CrossEncoderReranker()

            RetrieverAgent._initialized = True
            logger.info(
                "RetrieverAgent RAG initialisé",
                chunks_milvus=stats.get("num_entities", 0),
                chunks_bm25=len(RetrieverAgent._chunks or []),
            )

        except Exception as e:
            logger.error("Erreur init RetrieverAgent", error=str(e))
            RetrieverAgent._initialized = False

    def _rrf_fusion(self, dense, sparse, k=60):
        """Reciprocal Rank Fusion."""
        scores = {}
        docs = {}

        for rank, r in enumerate(dense):
            cid = r["chunk_id"]
            scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
            docs[cid] = r

        for rank, r in enumerate(sparse):
            cid = r["chunk_id"]
            scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
            if cid not in docs:
                docs[cid] = r

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [docs[cid] for cid, _ in ranked]

    def retrieve(self, state: AgentState) -> AgentState:
        """Nœud LangGraph : retrieval RAG complet."""
        t_start = time.time()
        query = state["query"]

        logger.info("RetrieverAgent démarre", query=query[:80])

        # Fallback si non initialisé
        if not RetrieverAgent._initialized:
            self._setup()
            if not RetrieverAgent._initialized:
                return {
                    **state,
                    "retrieved_context": self._fallback_context(query),
                    "action_history": [{"agent": "retriever", "action": "fallback"}],
                }

        try:
            # 1. Dense search
            dense_results = RetrieverAgent._vector_store.dense_search(
                query=query, top_k=15
            )

            # 2. BM25 sparse search
            sparse_results = []
            if RetrieverAgent._bm25:
                sparse_results = RetrieverAgent._bm25.search(query=query, top_k=15)

            # 3. RRF Fusion
            if sparse_results:
                fused = self._rrf_fusion(dense_results, sparse_results)
            else:
                fused = dense_results

            candidates = fused[:20]

            # 4. Reranking Cross-Encoder
            if RetrieverAgent._reranker and candidates:
                reranked = RetrieverAgent._reranker.rerank(
                    query=query,
                    candidates=candidates,
                    top_k=self.top_k,
                )
            else:
                reranked = candidates[:self.top_k]

            # 5. Construire contexte avec citations
            context = self._build_context_with_citations(query, reranked)

            latency = round((time.time() - t_start) * 1000, 2)

            logger.info(
                "RetrieverAgent terminé",
                query=query[:60],
                chunks=len(reranked),
                latency_ms=latency,
            )

            return {
                **state,
                "retrieved_context": context,
                "action_history": [{
                    "agent": "retriever",
                    "action": "rag_retrieve",
                    "chunks_retrieved": len(reranked),
                    "latency_ms": latency,
                    "dense_count": len(dense_results),
                    "sparse_count": len(sparse_results),
                }],
                "metadata": {
                    **state.get("metadata", {}),
                    "retriever_latency_ms": latency,
                    "chunks_retrieved": len(reranked),
                },
            }

        except Exception as e:
            logger.error("Erreur RetrieverAgent", error=str(e))
            return {
                **state,
                "retrieved_context": self._fallback_context(query),
                "errors": [f"RetrieverAgent error: {str(e)}"],
                "action_history": [{"agent": "retriever", "action": "error", "error": str(e)}],
            }

    def _build_context_with_citations(self, query: str, chunks: list) -> str:
        """Formate les chunks avec citations de source."""
        if not chunks:
            return self._fallback_context(query)

        parts = [f"Documentation technique — {len(chunks)} sources pertinentes :\n"]

        for i, chunk in enumerate(chunks):
            score = chunk.get("cross_encoder_score", chunk.get("rrf_score", 0))
            section = chunk.get("section", "") or ""
            content = chunk.get("content", "")

            source_label = f"[Source {i+1}"
            if section:
                source_label += f" · {section[:50]}"
            source_label += f" · pertinence: {score:.2f}]"

            parts.append(f"\n{source_label}\n{content}")

        parts.append(
            "\n\n📌 Source : Description du procédé de fabrication — Aciérie Maghreb Steel"
        )
        return "\n".join(parts)

    def _fallback_context(self, query: str) -> str:
        """Contexte de fallback depuis la connaissance du LLM."""
        return """Documentation Aciérie Maghreb Steel — Informations générales :

[Source 1 · Procédé EAF]
Le four EAF (Electric Arc Furnace) est un four de fusion utilisant des arcs électriques.
Puissance : 120 MVA · 3 électrodes en graphite.
Étapes : Chargement ferraille → Fusion → Affinage → Tapping.

[Source 2 · Procédé LF]
Le four LF (Ladle Furnace) est un four de traitement secondaire (20 MVA).
Rôle : Désulfuration, mise à nuance, réglage température avant CCM.

[Source 3 · Procédé CCM]
La Coulée Continue (CCM) solidifie l'acier liquide en brames (slabs).
Composants : Ladle turret, Tundish, Moule, Oxycoupage, Machine de marquage.

[Source 4 · PAF]
Le Parc à Ferraille (PAF) stocke et prépare la ferraille avant enfournement.
Zones : Réception, Stockage (boxes), Oxycoupage, Cisaille, Broyage.

📌 Source : Documentation technique Aciérie Maghreb Steel"""