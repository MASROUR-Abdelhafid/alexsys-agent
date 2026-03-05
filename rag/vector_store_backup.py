"""
Module Vector Store — Milvus.
Index HNSW + stockage chunks avec métadonnées.
Phase 1 - Étape 1.2
"""

from typing import List, Dict, Any, Optional
from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility,
)
import structlog

from config import config
from rag.embeddings import EmbeddingModel, EMBEDDING_DIM

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "alexsys_knowledge"


class MilvusVectorStore:
    """
    Gestion de la collection Milvus pour le RAG.
    
    Schema :
        - chunk_id     : VARCHAR PK
        - embedding    : FLOAT_VECTOR(384)
        - content      : VARCHAR(4096)
        - source       : VARCHAR(512)
        - chunk_index  : INT64
        - section      : VARCHAR(512)
    """

    def __init__(self):
        self.embedding_model = EmbeddingModel()
        self.collection: Optional[Collection] = None
        self._connect()

    def _connect(self):
        """Connexion à Milvus."""
        connections.connect(
            alias="default",
            host=config.MILVUS_HOST,
            port=config.MILVUS_PORT,
        )
        logger.info(
            "Connecté à Milvus",
            host=config.MILVUS_HOST,
            port=config.MILVUS_PORT,
        )

    def _build_schema(self) -> CollectionSchema:
        """Définit le schéma de la collection."""
        fields = [
            FieldSchema(
                name="chunk_id",
                dtype=DataType.VARCHAR,
                max_length=64,
                is_primary=True,
                auto_id=False,
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=EMBEDDING_DIM,
            ),
            FieldSchema(
                name="content",
                dtype=DataType.VARCHAR,
                max_length=4096,
            ),
            FieldSchema(
                name="source",
                dtype=DataType.VARCHAR,
                max_length=512,
            ),
            FieldSchema(
                name="chunk_index",
                dtype=DataType.INT64,
            ),
            FieldSchema(
                name="section",
                dtype=DataType.VARCHAR,
                max_length=512,
            ),
        ]
        return CollectionSchema(
            fields=fields,
            description="Alexsys knowledge base — RAG multi-agentique",
        )

    def create_collection(self, drop_if_exists: bool = False):
        """Crée la collection Milvus avec index HNSW."""
        if utility.has_collection(COLLECTION_NAME):
            if drop_if_exists:
                utility.drop_collection(COLLECTION_NAME)
                logger.info("Collection supprimée", name=COLLECTION_NAME)
            else:
                logger.info("Collection existante chargée", name=COLLECTION_NAME)
                self.collection = Collection(COLLECTION_NAME)
                self.collection.load()
                return

        schema = self._build_schema()
        self.collection = Collection(
            name=COLLECTION_NAME,
            schema=schema,
        )

        # Index HNSW — O(log n) search, optimal pour RAG
        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {
                "M": 16,           # Nb connexions par nœud
                "efConstruction": 200,  # Qualité construction index
            },
        }
        self.collection.create_index(
            field_name="embedding",
            index_params=index_params,
        )
        self.collection.load()

        logger.info(
            "Collection créée avec index HNSW",
            name=COLLECTION_NAME,
            dim=EMBEDDING_DIM,
        )

    def insert_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """
        Insère des chunks dans Milvus.

        Args:
            chunks: liste de dicts {content, metadata}

        Returns:
            Nombre de chunks insérés
        """
        if not self.collection:
            raise RuntimeError("Collection non initialisée. Appelle create_collection() d'abord.")

        # Préparer les textes pour embedding
        texts = [c["content"] for c in chunks]

        logger.info("Génération des embeddings...", count=len(texts))
        embeddings = self.embedding_model.encode(
            texts,
            batch_size=32,
            show_progress=True,
        )

        # Préparer les données pour insertion
        data = [
            [c["metadata"]["chunk_id"] for c in chunks],        # chunk_id
            embeddings.tolist(),                                   # embedding
            [c["content"][:4000] for c in chunks],               # content
            [c["metadata"]["source"] for c in chunks],           # source
            [c["metadata"]["chunk_index"] for c in chunks],      # chunk_index
            [c["metadata"].get("section", "") or "" for c in chunks],  # section
        ]

        self.collection.insert(data)
        self.collection.flush()

        count = self.collection.num_entities
        logger.info("Chunks insérés", inserted=len(chunks), total=count)
        return len(chunks)

    def dense_search(
        self,
        query: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Recherche vectorielle dense (cosine similarity).

        Args:
            query: question utilisateur
            top_k: nombre de résultats

        Returns:
            Liste de résultats avec score et contenu
        """
        query_embedding = self.embedding_model.encode_single(query)

        search_params = {
            "metric_type": "COSINE",
            "params": {"ef": 64},  # efSearch — qualité vs vitesse
        }

        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["content", "source", "chunk_index", "section"],
        )

        hits = []
        for hit in results[0]:
            hits.append({
                "chunk_id": hit.id,
                "content": hit.entity.get("content"),
                "source": hit.entity.get("source"),
                "chunk_index": hit.entity.get("chunk_index"),
                "section": hit.entity.get("section"),
                "score": float(hit.score),
                "retrieval_type": "dense",
            })

        logger.debug("Dense search terminée", query=query[:50], results=len(hits))
        return hits

    def get_collection_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de la collection."""
        if not self.collection:
            return {}
        return {
            "name": COLLECTION_NAME,
            "num_entities": self.collection.num_entities,
            "embedding_dim": EMBEDDING_DIM,
            "index_type": "HNSW",
            "metric": "COSINE",
        }