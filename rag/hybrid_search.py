"""
Module Hybrid Search — Fusion Dense + Sparse via RRF.
Phase 1 - Étape 1.4
"""

from typing import List, Dict, Any, Optional
import numpy as np
import structlog

from rag.vector_store import MilvusVectorStore
from rag.sparse_retrieval import BM25Retriever
from rag.ingestion import DocumentIngestionPipeline

logger = structlog.get_logger(__name__)


class HybridSearchEngine:
    """
    Moteur de recherche hybride Dense + Sparse.

    Pipeline :
    1. Dense search  → top-K via Milvus HNSW (sémantique)
    2. Sparse search → top-K via BM25 (lexical)
    3. RRF Fusion    → score unifié et re-ranking
    """

    def __init__(
        self,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5,
        rrf_k: int = 60,
    ):
        """
        Args:
            dense_weight : poids résultats dense dans fusion (0-1)
            sparse_weight: poids résultats sparse dans fusion (0-1)
            rrf_k        : constante RRF (60 recommandé par Cormack)
        """
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.rrf_k = rrf_k

        # Composants
        self.vector_store = MilvusVectorStore()
        self.bm25_retriever = BM25Retriever()
        self._bm25_indexed = False

        logger.info(
            "HybridSearchEngine initialisé",
            dense_weight=dense_weight,
            sparse_weight=sparse_weight,
            rrf_k=rrf_k,
        )

    def build_bm25_index(self, chunks: Optional[List[Dict[str, Any]]] = None):
        """
        Construit l'index BM25.
        Si chunks=None, recharge depuis le fichier source.
        """
        if chunks is None:
            pipeline = DocumentIngestionPipeline()
            chunks = pipeline.ingest("data/sample/alexsys_knowledge_base.txt")

        self.bm25_retriever.index(chunks)
        self._bm25_indexed = True
        logger.info("Index BM25 construit pour hybrid search", docs=len(chunks))

    def _rrf_fusion(
        self,
        dense_results: List[Dict[str, Any]],
        sparse_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion.

        RRF_score(d) = w_dense × 1/(k + rank_dense(d))
                     + w_sparse × 1/(k + rank_sparse(d))
        """
        # Construire dict chunk_id → données
        all_chunks: Dict[str, Dict[str, Any]] = {}

        for rank, result in enumerate(dense_results):
            cid = result["chunk_id"]
            if cid not in all_chunks:
                all_chunks[cid] = result.copy()
                all_chunks[cid]["rrf_score"] = 0.0
                all_chunks[cid]["dense_rank"] = None
                all_chunks[cid]["sparse_rank"] = None
            all_chunks[cid]["dense_rank"] = rank + 1
            all_chunks[cid]["rrf_score"] += (
                self.dense_weight * (1.0 / (self.rrf_k + rank + 1))
            )

        for rank, result in enumerate(sparse_results):
            cid = result["chunk_id"]
            if cid not in all_chunks:
                all_chunks[cid] = result.copy()
                all_chunks[cid]["rrf_score"] = 0.0
                all_chunks[cid]["dense_rank"] = None
                all_chunks[cid]["sparse_rank"] = None
            all_chunks[cid]["sparse_rank"] = rank + 1
            all_chunks[cid]["rrf_score"] += (
                self.sparse_weight * (1.0 / (self.rrf_k + rank + 1))
            )

        # Trier par score RRF décroissant
        fused = sorted(
            all_chunks.values(),
            key=lambda x: x["rrf_score"],
            reverse=True,
        )

        # Ajouter métadonnée retrieval_type
        for item in fused:
            d_rank = item.get("dense_rank")
            s_rank = item.get("sparse_rank")
            if d_rank and s_rank:
                item["retrieval_type"] = "hybrid"
            elif d_rank:
                item["retrieval_type"] = "dense_only"
            else:
                item["retrieval_type"] = "sparse_only"

        return fused

    def search(
        self,
        query: str,
        top_k: int = 5,
        dense_candidates: int = 20,
        sparse_candidates: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Recherche hybride complète.

        Args:
            query            : question utilisateur
            top_k            : résultats finaux après fusion
            dense_candidates : candidats dense avant fusion
            sparse_candidates: candidats sparse avant fusion

        Returns:
            Top-K chunks fusionnés et re-rankés par RRF
        """
        if not self._bm25_indexed:
            self.build_bm25_index()

        # 1. Dense retrieval
        dense_results = self.vector_store.dense_search(
            query=query,
            top_k=dense_candidates,
        )

        # 2. Sparse retrieval
        sparse_results = self.bm25_retriever.search(
            query=query,
            top_k=sparse_candidates,
        )

        # 3. RRF Fusion
        fused_results = self._rrf_fusion(dense_results, sparse_results)

        # 4. Top-K final
        final_results = fused_results[:top_k]

        logger.info(
            "Hybrid search terminée",
            query=query[:60],
            dense_candidates=len(dense_results),
            sparse_candidates=len(sparse_results),
            fused_total=len(fused_results),
            final_top_k=len(final_results),
        )

        return final_results

    def search_with_analysis(
        self,
        query: str,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Recherche hybride avec analyse comparative dense vs sparse.
        Utile pour le benchmark et la validation expérimentale.
        """
        if not self._bm25_indexed:
            self.build_bm25_index()

        dense_results = self.vector_store.dense_search(query=query, top_k=10)
        sparse_results = self.bm25_retriever.search(query=query, top_k=10)
        hybrid_results = self._rrf_fusion(dense_results, sparse_results)[:top_k]

        return {
            "query": query,
            "dense_results": dense_results[:top_k],
            "sparse_results": sparse_results[:top_k],
            "hybrid_results": hybrid_results,
            "analysis": {
                "dense_only": sum(
                    1 for r in hybrid_results
                    if r["retrieval_type"] == "dense_only"
                ),
                "sparse_only": sum(
                    1 for r in hybrid_results
                    if r["retrieval_type"] == "sparse_only"
                ),
                "hybrid": sum(
                    1 for r in hybrid_results
                    if r["retrieval_type"] == "hybrid"
                ),
            },
        }