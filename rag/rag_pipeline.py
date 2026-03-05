"""
Pipeline RAG complet :
Hybrid Search → Re-ranking → Contexte pour LLM.
Phase 1 - Étape 1.5
"""

import time
from typing import List, Dict, Any, Optional
import structlog

from rag.hybrid_search import HybridSearchEngine
from rag.reranker import CrossEncoderReranker

logger = structlog.get_logger(__name__)


class RAGPipeline:
    """
    Pipeline RAG complet industriel.

    Étapes :
    1. Hybrid Search  : Dense + Sparse → RRF fusion (20 candidats)
    2. Re-ranking     : Cross-Encoder → Top-5 précis
    3. Context build  : Formatage contexte pour LLM
    """

    def __init__(
        self,
        hybrid_candidates: int = 20,
        rerank_top_k: int = 5,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5,
    ):
        self.hybrid_candidates = hybrid_candidates
        self.rerank_top_k = rerank_top_k

        self.hybrid_engine = HybridSearchEngine(
            dense_weight=dense_weight,
            sparse_weight=sparse_weight,
        )
        self.reranker = CrossEncoderReranker()
        logger.info(
            "RAGPipeline initialisé",
            hybrid_candidates=hybrid_candidates,
            rerank_top_k=rerank_top_k,
        )

    def build_index(self):
        """Construit les index (BM25)."""
        self.hybrid_engine.build_bm25_index()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        return_metadata: bool = True,
    ) -> Dict[str, Any]:
        """
        Retrieval complet avec métriques de latence.

        Returns:
            {
                chunks      : List[Dict] top-K chunks re-rankés,
                context     : str contexte formaté pour LLM,
                metadata    : Dict métriques pipeline,
            }
        """
        t_start = time.time()

        # 1. Hybrid Search
        t0 = time.time()
        candidates = self.hybrid_engine.search(
            query=query,
            top_k=self.hybrid_candidates,
        )
        t_hybrid = time.time() - t0

        # 2. Re-ranking
        t0 = time.time()
        reranked = self.reranker.rerank(
            query=query,
            candidates=candidates,
            top_k=top_k,
        )
        t_rerank = time.time() - t0

        t_total = time.time() - t_start

        # 3. Construire contexte
        context = self._build_context(reranked)

        metadata = {
            "query": query,
            "total_latency_ms": round(t_total * 1000, 2),
            "hybrid_latency_ms": round(t_hybrid * 1000, 2),
            "rerank_latency_ms": round(t_rerank * 1000, 2),
            "candidates_retrieved": len(candidates),
            "chunks_reranked": len(reranked),
            "top_cross_encoder_score": (
                reranked[0]["cross_encoder_score"] if reranked else 0
            ),
            "retrieval_types": [r["retrieval_type"] for r in reranked],
        }

        logger.info("RAG Pipeline retrieve", **metadata)

        return {
            "chunks": reranked,
            "context": context,
            "metadata": metadata,
        }

    def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Formate les chunks en contexte structuré pour le LLM."""
        if not chunks:
            return "Aucun contexte pertinent trouvé."

        parts = []
        for i, chunk in enumerate(chunks):
            section = chunk.get("section", "")
            section_str = f" [{section}]" if section else ""
            parts.append(
                f"[Source {i+1}{section_str}]\n{chunk['content']}"
            )

        return "\n\n---\n\n".join(parts)