"""
Agent Retriever — Nœud RAG du graphe LangGraph.
Intègre Hybrid Search + Cross-Encoder Reranker.
Phase 2 - Étape 2.2
"""

import time
from typing import Dict, Any
import structlog

from agents.state import AgentState
from rag.rag_pipeline import RAGPipeline

logger = structlog.get_logger(__name__)


class RetrieverAgent:
    """
    Agent Retriever — Nœud RAG dans le graphe agentique.

    Responsabilités :
    1. Extraire la query depuis l'état
    2. Exécuter le pipeline RAG complet
    3. Injecter le contexte dans l'état
    4. Logger les métriques de retrieval
    """

    def __init__(
        self,
        hybrid_candidates: int = 20,
        rerank_top_k: int = 5,
    ):
        self.pipeline = RAGPipeline(
            hybrid_candidates=hybrid_candidates,
            rerank_top_k=rerank_top_k,
        )
        self.pipeline.build_index()
        logger.info(
            "RetrieverAgent initialisé",
            hybrid_candidates=hybrid_candidates,
            rerank_top_k=rerank_top_k,
        )

    def retrieve(self, state: AgentState) -> AgentState:
        """
        Nœud LangGraph : retrieval RAG complet.

        Args:
            state: état courant du graphe

        Returns:
            état enrichi avec retrieved_context et métriques
        """
        t_start = time.time()
        query = state["query"]

        logger.info("RetrieverAgent démarre", query=query[:80])

        try:
            result = self.pipeline.retrieve(
                query=query,
                top_k=5,
            )

            context = result["context"]
            rag_metadata = result["metadata"]
            chunks = result["chunks"]

            latency = round((time.time() - t_start) * 1000, 2)

            # Résumé des chunks récupérés
            chunks_summary = [
                {
                    "chunk_id": c.get("chunk_id", ""),
                    "section": c.get("section", ""),
                    "score": c.get("cross_encoder_score", 0),
                    "retrieval_type": c.get("retrieval_type", ""),
                }
                for c in chunks
            ]

            logger.info(
                "RetrieverAgent terminé",
                query=query[:60],
                chunks=len(chunks),
                latency_ms=latency,
                top_score=rag_metadata.get("top_cross_encoder_score", 0),
            )

            return {
                **state,
                "retrieved_context": context,
                "action_history": [{
                    "agent": "retriever",
                    "action": "rag_retrieve",
                    "chunks_retrieved": len(chunks),
                    "chunks_summary": chunks_summary,
                    "latency_ms": latency,
                    "rag_metadata": rag_metadata,
                }],
                "metadata": {
                    **state.get("metadata", {}),
                    "retriever_latency_ms": latency,
                    "rag_pipeline": rag_metadata,
                },
            }

        except Exception as e:
            logger.error("Erreur RetrieverAgent", error=str(e))
            return {
                **state,
                "retrieved_context": "",
                "errors": [f"RetrieverAgent error: {str(e)}"],
                "action_history": [{
                    "agent": "retriever",
                    "action": "error",
                    "error": str(e),
                }],
            }