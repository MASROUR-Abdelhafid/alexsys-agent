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

    def __init__(self):
        self.embedding_model = EmbeddingModel()
        self.collection: Optional[Collection] = None
        self._connect()

    def _connect(self):
        """Connexion à Milvus + chargement collection si existante."""
        connections.connect(
            alias="default",
            host=config.MILVUS_HOST,
            port=config.MILVUS_PORT,
        )
        logger.info("Connecté à Milvus", host=config.MILVUS_HOST, port=config.MILVUS_PORT)

        if utility.has_collection(COLLECTION_NAME):
            self.collection = Collection(COLLECTION_NAME)
            self.collection.load()
            logger.info("Collection existante chargée", name=COLLECTION_NAME)

    def _build_schema(self) -> CollectionSchema:
        fields = [
            FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=64, is_primary=True, auto_id=False),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=512),
        ]
        return CollectionSchema(fields=fields, description="Alexsys knowledge base")

    def create_collection(self, drop_if_exists: bool = False):
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
        self.collection = Collection(name=COLLECTION_NAME, schema=schema)

        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 16, "efConstruction": 200},
        }
        self.collection.create_index(field_name="embedding", index_params=index_params)
        self.collection.load()
        logger.info("Collection créée avec index HNSW", name=COLLECTION_NAME, dim=EMBEDDING_DIM)

    def insert_chunks(self, chunks: list) -> int:
        """Insère les chunks dans Milvus."""
        if not chunks:
            return 0
        
        # Utiliser embedding_model.encode() au lieu de _embed()
        embeddings = self.embedding_model.encode([c["content"] for c in chunks])
        
        data = [
            [c.get("chunk_id", "") for c in chunks],
            embeddings.tolist(),  # Les embeddings viennent AVANT content dans le schema
            [c["content"] for c in chunks],
            [c.get("source", "") for c in chunks],
            [int(c.get("chunk_index", 0) or 0) for c in chunks],
            [c.get("section", "") or "" for c in chunks],
        ]
        
        self.collection.insert(data)
        self.collection.flush()
        inserted = len(chunks)
        logger.info("Chunks insérés", inserted=inserted, total=len(chunks))
        return inserted

    def dense_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        if not self.collection:
            raise RuntimeError("Collection non initialisée.")

        query_embedding = self.embedding_model.encode_single(query)

        search_params = {
            "metric_type": "COSINE",
            "params": {"ef": 64},
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
        if not self.collection:
            return {}
        return {
            "name": COLLECTION_NAME,
            "num_entities": self.collection.num_entities,
            "embedding_dim": EMBEDDING_DIM,
            "index_type": "HNSW",
            "metric": "COSINE",
        }