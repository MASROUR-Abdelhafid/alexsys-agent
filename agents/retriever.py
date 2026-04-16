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
        scores = {}
        docs = {}
        for rank, r in enumerate(dense):
            # chunk_id peut être dans r directement ou r["metadata"]
            cid = r.get("chunk_id") or r.get("id", f"d{rank}")
            scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
            docs[cid] = r
        for rank, r in enumerate(sparse):
            cid = r.get("chunk_id") or r.get("id", f"s{rank}")
            scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
            if cid not in docs:
                docs[cid] = r
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [docs[cid] for cid, _ in ranked]

    def retrieve(self, state: AgentState) -> AgentState:
        t_start = time.time()
        query = state["query"]
        logger.info("RetrieverAgent démarre", query=query[:80])

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
            dense_results = RetrieverAgent._vector_store.dense_search(query=query, top_k=15)

            # 2. Normaliser tous les résultats — supprimer "metadata" si présent
            def normalize(chunk):
                if "metadata" in chunk and isinstance(chunk["metadata"], dict):
                    flat = {**chunk}
                    for k, v in chunk["metadata"].items():
                        if k not in flat:
                            flat[k] = v
                    del flat["metadata"]
                    return flat
                return chunk

            dense_results = [normalize(c) for c in dense_results]

            # 3. BM25 sparse search
            sparse_results = []
            if RetrieverAgent._bm25:
                sparse_results = RetrieverAgent._bm25.search(query=query, top_k=15)
                sparse_results = [normalize(c) for c in sparse_results]

            # 4. RRF Fusion
            fused = self._rrf_fusion(dense_results, sparse_results) if sparse_results else dense_results
            candidates = fused[:20]

            # 5. Reranking
            if RetrieverAgent._reranker and candidates:
                reranked = RetrieverAgent._reranker.rerank(
                    query=query, candidates=candidates, top_k=self.top_k
                )
                reranked = [normalize(c) for c in reranked]
            else:
                reranked = candidates[:self.top_k]

            context = self._build_context_with_citations(query, reranked)
            latency = round((time.time() - t_start) * 1000, 2)

            logger.info("RetrieverAgent terminé", chunks=len(reranked),
                        latency_ms=latency, query=query[:60])

            return {
                **state,
                "retrieved_context": context,
                "action_history": [{
                    "agent": "retriever",
                    "action": "rag_retrieve",
                    "chunks_retrieved": len(reranked),
                    "latency_ms": latency,
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

    # Dans _build_context_with_citations, remplace l'accès aux champs :
    def _build_context_with_citations(self, query: str, chunks: list) -> str:
        if not chunks:
            return self._fallback_context(query)

        parts = [f"Documentation technique — {len(chunks)} sources pertinentes :\n"]

        for i, chunk in enumerate(chunks):
            # Compatibilité : accès direct ou via metadata
            if "metadata" in chunk:
                score   = chunk.get("cross_encoder_score", chunk.get("rrf_score", 0))
                section = chunk["metadata"].get("section", "") or ""
                page    = chunk["metadata"].get("page", "?")
                content = chunk.get("content", "")
                source  = chunk["metadata"].get("source", "PDF Aciérie")
            else:
                score   = chunk.get("cross_encoder_score", chunk.get("rrf_score", chunk.get("score", 0)))
                section = chunk.get("section", "") or ""
                page    = chunk.get("page", "?")
                content = chunk.get("content", "")
                source  = chunk.get("source", "PDF Aciérie")

            label = f"[Source {i+1}"
            if section:
                label += f" · {section[:50]}"
            label += f" · page {page} · pertinence: {score:.2f}]"
            parts.append(f"\n{label}\n{content}")

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