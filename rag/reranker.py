"""
Module Re-ranking — Cross-Encoder.
Affinage précision après Hybrid Search.
Phase 1 - Étape 1.5
"""

from typing import List, Dict, Any, Optional
import numpy as np
import structlog

logger = structlog.get_logger(__name__)

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class CrossEncoderReranker:
    """
    Re-ranker basé sur Cross-Encoder.

    Pipeline :
    1. Reçoit candidats du Hybrid Search (~20)
    2. Score chaque paire (query, doc) conjointement
    3. Retourne Top-K re-rankés

    Justification du modèle :
    - ms-marco-MiniLM-L-6-v2 : entraîné sur MS MARCO (passage ranking)
    - 6 layers MiniLM : rapide (22ms/pair CPU) vs large models
    - Score logit → interprétable comme relevance score
    """

    _instance = None

    def __new__(cls, model_name: str = RERANKER_MODEL):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: str = RERANKER_MODEL):
        if self._initialized:
            return
        self.model_name = model_name
        logger.info("Chargement Cross-Encoder...", model=model_name)

        from sentence_transformers import CrossEncoder
        self.model = CrossEncoder(model_name, max_length=512)
        self._initialized = True
        logger.info("Cross-Encoder chargé", model=model_name)

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Re-rank les candidats par pertinence (query, doc).

        Args:
            query           : question utilisateur
            candidates      : chunks issus du Hybrid Search
            top_k           : nombre final de chunks à retourner
            score_threshold : seuil minimum de score (optionnel)

        Returns:
            Top-K chunks re-rankés avec cross_encoder_score
        """
        if not candidates:
            return []

        # Construire paires (query, doc)
        pairs = [(query, c["content"]) for c in candidates]

        # Scoring cross-encoder
        scores = self.model.predict(pairs)

        # Enrichir les candidats avec le score
        scored = []
        for i, candidate in enumerate(candidates):
            enriched = candidate.copy()
            enriched["cross_encoder_score"] = float(scores[i])
            enriched["original_rank"] = i + 1
            scored.append(enriched)

        # Trier par cross_encoder_score décroissant
        scored.sort(key=lambda x: x["cross_encoder_score"], reverse=True)

        # Appliquer seuil si défini
        if score_threshold is not None:
            scored = [s for s in scored if s["cross_encoder_score"] >= score_threshold]

        # Top-K final
        result = scored[:top_k]

        # Ajouter rang final
        for rank, item in enumerate(result):
            item["final_rank"] = rank + 1
            item["rank_change"] = item["original_rank"] - (rank + 1)

        logger.info(
            "Re-ranking terminé",
            query=query[:60],
            candidates_in=len(candidates),
            results_out=len(result),
            top_score=float(scores.max()) if len(scores) > 0 else 0,
        )

        return result

    def compute_relevance_score(
        self, query: str, document: str
    ) -> float:
        """Score de pertinence pour une seule paire (query, doc)."""
        score = self.model.predict([(query, document)])
        return float(score[0])