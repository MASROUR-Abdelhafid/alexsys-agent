"""
Module de génération d'embeddings.
Modèle : all-MiniLM-L6-v2 (384 dims)
Phase 1 - Étape 1.2
"""

from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import structlog

logger = structlog.get_logger(__name__)

# Modèle par défaut — rapport performance/vitesse optimal pour RAG
DEFAULT_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


class EmbeddingModel:
    """
    Wrapper autour de SentenceTransformer.
    Singleton pattern pour éviter les rechargements coûteux.
    """

    _instance = None

    def __new__(cls, model_name: str = DEFAULT_MODEL):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: str = DEFAULT_MODEL):
        if self._initialized:
            return
        self.model_name = model_name
        logger.info("Chargement du modèle d'embeddings...", model=model_name)
        self.model = SentenceTransformer(model_name)
        self._initialized = True
        logger.info("Modèle chargé", model=model_name, dim=EMBEDDING_DIM)

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress: bool = False,
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Encode un texte ou une liste de textes en vecteurs.

        Args:
            texts: texte(s) à encoder
            batch_size: taille des batches (optimise RAM/vitesse)
            show_progress: afficher barre de progression
            normalize: normaliser L2 (recommandé pour cosine similarity)

        Returns:
            numpy array de shape (n, 384)
        """
        if isinstance(texts, str):
            texts = [texts]

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=normalize,
            convert_to_numpy=True,
        )

        logger.debug(
            "Embeddings générés",
            count=len(texts),
            shape=embeddings.shape,
        )
        return embeddings

    def encode_single(self, text: str) -> List[float]:
        """Encode un seul texte → liste float (format Milvus)."""
        return self.encode(text)[0].tolist()

    @property
    def dimension(self) -> int:
        return EMBEDDING_DIM