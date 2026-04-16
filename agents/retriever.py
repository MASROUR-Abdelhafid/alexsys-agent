"""
Agent Retriever — RAG Pipeline Aciérie.
Hybrid Search + Cross-Encoder sur documentation technique.
"""

import time
from typing import Dict, Any, List
import structlog

from agents.state import AgentState
from rag.vector_store import MilvusVectorStore
from rag.sparse_retrieval import BM25Retriever
from rag.ingestion import DocumentIngestionPipeline, IngestionConfig
from rag.reranker import CrossEncoderReranker

logger = structlog.get_logger(__name__)


def _normalize_chunk(chunk: dict) -> dict:
    """
    Normalise un chunk : aplatit metadata imbriquée si présente.
    Assure que content, section, page, source, chunk_id sont au niveau racine.
    """
    if not isinstance(chunk, dict):
        return {"content": str(chunk), "section": "", "page": 1, "source": ""}

    # Si metadata est imbriqué, on l'aplatit
    if "metadata" in chunk and isinstance(chunk["metadata"], dict):
        flat = {}
        # Copier d'abord les champs racine (hors metadata)
        for k, v in chunk.items():
            if k != "metadata":
                flat[k] = v
        # Puis les champs metadata (sans écraser ceux déjà présents)
        for k, v in chunk["metadata"].items():
            if k not in flat:
                flat[k] = v
        return flat

    return chunk


class RetrieverAgent:
    """
    Agent Retriever — Recherche dans la documentation aciérie.
    Pipeline : Dense → BM25 → RRF → Cross-Encoder → Citations
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
            RetrieverAgent._vector_store = MilvusVectorStore()
            stats = RetrieverAgent._vector_store.get_collection_stats()

            if stats.get("num_entities", 0) == 0:
                logger.warning("Collection Milvus vide — indexation nécessaire")
                RetrieverAgent._initialized = False
                return

            # BM25 — indexer depuis PDF
            import os
            config = IngestionConfig(chunk_size=600, chunk_overlap=80)
            pipeline = DocumentIngestionPipeline(config)

            pdf_path = "data/acierie/Description_du_processus_acierie.pdf"
            if not os.path.exists(pdf_path):
                pdf_path = "data/acierie/Description_du_processus_aciérie.pdf"

            if os.path.exists(pdf_path):
                raw_chunks = pipeline.ingest(pdf_path)
                # Normaliser les chunks BM25
                RetrieverAgent._chunks = [_normalize_chunk(c) for c in raw_chunks]
                bm25 = BM25Retriever()
                bm25.index(RetrieverAgent._chunks)
                RetrieverAgent._bm25 = bm25
                logger.info("BM25 indexé", docs=len(RetrieverAgent._chunks))

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

    def _rrf_fusion(self, dense: List[dict], sparse: List[dict], k: int = 60) -> List[dict]:
        """Reciprocal Rank Fusion."""
        scores = {}
        docs = {}
        for rank, r in enumerate(dense):
            cid = r.get("chunk_id") or r.get("id") or f"d{rank}"
            scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
            docs[cid] = r
        for rank, r in enumerate(sparse):
            cid = r.get("chunk_id") or r.get("id") or f"s{rank}"
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

        if not RetrieverAgent._initialized:
            self._setup()
            if not RetrieverAgent._initialized:
                return {
                    **state,
                    "retrieved_context": self._fallback_context(query),
                    "action_history": [{"agent": "retriever", "action": "fallback"}],
                }

        try:
            # 1. Dense search + normalisation immédiate
            raw_dense = RetrieverAgent._vector_store.dense_search(query=query, top_k=15)
            dense_results = [_normalize_chunk(c) for c in raw_dense]

            # 2. BM25 sparse search + normalisation immédiate
            sparse_results = []
            if RetrieverAgent._bm25:
                raw_sparse = RetrieverAgent._bm25.search(query=query, top_k=15)
                sparse_results = [_normalize_chunk(c) for c in raw_sparse]

            # 3. RRF Fusion
            if sparse_results:
                fused = self._rrf_fusion(dense_results, sparse_results)
            else:
                fused = dense_results
            candidates = fused[:20]

            # Vérification que tous les candidats ont "content"
            candidates = [c for c in candidates if c.get("content")]

            # 4. Reranking Cross-Encoder
            if RetrieverAgent._reranker and candidates:
                reranked = RetrieverAgent._reranker.rerank(
                    query=query,
                    candidates=candidates,
                    top_k=self.top_k,
                )
                reranked = [_normalize_chunk(c) for c in reranked]
            else:
                reranked = candidates[:self.top_k]

            # 5. Construire contexte avec citations
            context = self._build_context_with_citations(query, reranked)
            latency = round((time.time() - t_start) * 1000, 2)

            logger.info(
                "RetrieverAgent terminé",
                chunks=len(reranked),
                latency_ms=latency,
                query=query[:60],
            )

            return {
                **state,
                "retrieved_context": context,
                "action_history": [{
                    "agent":            "retriever",
                    "action":           "rag_retrieve",
                    "chunks_retrieved": len(reranked),
                    "latency_ms":       latency,
                    "dense_count":      len(dense_results),
                    "sparse_count":     len(sparse_results),
                }],
                "metadata": {
                    **state.get("metadata", {}),
                    "retriever_latency_ms": latency,
                    "chunks_retrieved":     len(reranked),
                },
            }

        except Exception as e:
            logger.error("Erreur RetrieverAgent", error=str(e))
            return {
                **state,
                "retrieved_context": self._fallback_context(query),
                "errors": [f"RetrieverAgent error: {str(e)}"],
                "action_history": [{
                    "agent":  "retriever",
                    "action": "error",
                    "error":  str(e),
                }],
            }

    def _build_context_with_citations(self, query: str, chunks: list) -> str:
        """Formate les chunks avec citations de source et numéro de page."""
        if not chunks:
            return self._fallback_context(query)

        parts = [f"Documentation technique — {len(chunks)} sources pertinentes :\n"]

        for i, chunk in enumerate(chunks):
            # Tous les chunks sont déjà normalisés (pas de metadata imbriquée)
            score   = chunk.get("cross_encoder_score",
                       chunk.get("rrf_score",
                       chunk.get("score", 0.0)))
            section = (chunk.get("section") or "").strip()
            page    = chunk.get("page", "?")
            content = chunk.get("content", "")

            label = f"[Source {i+1}"
            if section:
                label += f" · {section[:60]}"
            label += f" · page {page} · pertinence: {score:.2f}]"
            parts.append(f"\n{label}\n{content}")

        parts.append(
            "\n\n📌 Source : Description du procédé de fabrication — Aciérie Maghreb Steel"
        )
        return "\n".join(parts)

    def _fallback_context(self, query: str) -> str:
        """Contexte de fallback si Milvus indisponible."""
        return """Documentation Aciérie Maghreb Steel — Informations générales :

[Source 1 · Procédé EAF · page 1]
Le four EAF (Electric Arc Furnace) est un four de fusion utilisant des arcs électriques.
Puissance : 120 MVA · 3 électrodes en graphite.
Étapes : Chargement ferraille → Fusion → Affinage → Tapping.

[Source 2 · Procédé LF · page 2]
Le four LF (Ladle Furnace) est un four de traitement secondaire (20 MVA).
Rôle : Désulfuration, mise à nuance, réglage température avant CCM.

[Source 3 · Procédé CCM · page 3]
La Coulée Continue (CCM) solidifie l'acier liquide en brames (slabs).
Composants : Ladle turret, Tundish, Moule, Oxycoupage, Machine de marquage.

[Source 4 · PAF · page 4]
Le Parc à Ferraille (PAF) stocke et prépare la ferraille avant enfournement.
Zones : Réception, Stockage (boxes), Oxycoupage, Cisaille, Broyage.

📌 Source : Documentation technique Aciérie Maghreb Steel"""