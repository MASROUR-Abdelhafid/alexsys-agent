"""
Module Sparse Retrieval — BM25.
Recherche lexicale complémentaire au dense retrieval.
Phase 1 - Étape 1.3
"""

import json
import pickle
import re
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
from rank_bm25 import BM25Okapi
import structlog

logger = structlog.get_logger(__name__)

# Stopwords français + anglais basiques
STOPWORDS = {
    "le", "la", "les", "de", "du", "des", "un", "une", "et", "en",
    "est", "à", "au", "aux", "que", "qui", "par", "pour", "sur",
    "the", "a", "an", "is", "in", "of", "to", "and", "for", "on",
    "with", "are", "was", "be", "has", "it", "this", "that", "or",
    "ce", "se", "sa", "son", "ses", "il", "elle", "ils", "elles",
    "nous", "vous", "je", "tu", "me", "te", "lui", "leur", "leurs",
}


class BM25Retriever:
    """
    Moteur de recherche sparse BM25.
    
    Stratégie :
    1. Tokenisation simple (lowercase + split)
    2. Suppression stopwords
    3. Indexation BM25Okapi (k1=1.5, b=0.75)
    4. Scoring et ranking
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.bm25: Optional[BM25Okapi] = None
        self.chunks: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []
        logger.info("BM25Retriever initialisé", k1=k1, b=b)

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenisation : lowercase, suppression ponctuation, stopwords.
        Conserve les termes techniques (acronymes, chiffres).
        """
        # Lowercase
        text = text.lower()
        # Garder lettres, chiffres, points (pour versions/pourcentages)
        text = re.sub(r'[^\w\s\.]', ' ', text)
        # Split
        tokens = text.split()
        # Filtrer stopwords et tokens trop courts (sauf acronymes)
        tokens = [
            t for t in tokens
            if t not in STOPWORDS and (len(t) > 2 or t.isupper())
        ]
        return tokens

    def index(self, chunks: List[Dict[str, Any]]):
        """
        Indexe une liste de chunks.

        Args:
            chunks: liste de dicts {content, metadata}
        """
        self.chunks = chunks
        self.tokenized_corpus = [
            self._tokenize(chunk["content"])
            for chunk in chunks
        ]

        self.bm25 = BM25Okapi(
            self.tokenized_corpus,
            k1=self.k1,
            b=self.b,
        )

        logger.info(
            "Index BM25 construit",
            num_docs=len(chunks),
            avg_tokens=int(np.mean([len(t) for t in self.tokenized_corpus])),
        )

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Recherche BM25 sur la query.

        Args:
            query: question utilisateur
            top_k: nombre de résultats

        Returns:
            Liste triée par score BM25 décroissant
        """
        if not self.bm25:
            raise RuntimeError("Index BM25 non construit. Appelle index() d'abord.")

        query_tokens = self._tokenize(query)

        if not query_tokens:
            logger.warning("Query vide après tokenisation", query=query)
            return []

        scores = self.bm25.get_scores(query_tokens)

        # Top-K indices
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score <= 0:
                continue
            chunk = self.chunks[idx]
            results.append({
                "chunk_id": chunk["metadata"]["chunk_id"],
                "content": chunk["content"],
                "source": chunk["metadata"]["source"],
                "chunk_index": chunk["metadata"]["chunk_index"],
                "section": chunk["metadata"].get("section", ""),
                "score": score,
                "retrieval_type": "sparse",
                "matched_tokens": [
                    t for t in query_tokens
                    if t in self.tokenized_corpus[idx]
                ],
            })

        logger.debug(
            "BM25 search terminée",
            query=query[:50],
            query_tokens=query_tokens,
            results=len(results),
        )
        return results

    def save(self, path: str):
        """Sauvegarde l'index BM25 sur disque."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({
                "bm25": self.bm25,
                "chunks": self.chunks,
                "tokenized_corpus": self.tokenized_corpus,
                "k1": self.k1,
                "b": self.b,
            }, f)
        logger.info("Index BM25 sauvegardé", path=path)

    @classmethod
    def load(cls, path: str) -> "BM25Retriever":
        """Charge un index BM25 depuis disque."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        retriever = cls(k1=data["k1"], b=data["b"])
        retriever.bm25 = data["bm25"]
        retriever.chunks = data["chunks"]
        retriever.tokenized_corpus = data["tokenized_corpus"]
        logger.info("Index BM25 chargé", path=path, docs=len(retriever.chunks))
        return retriever

    def get_stats(self) -> Dict[str, Any]:
        """Statistiques de l'index."""
        if not self.bm25:
            return {}
        return {
            "num_docs": len(self.chunks),
            "avg_tokens_per_doc": int(
                np.mean([len(t) for t in self.tokenized_corpus])
            ),
            "vocab_size": len(self.bm25.idf),
            "k1": self.k1,
            "b": self.b,
        }