"""
Mémoire Long-terme — Stockage vectoriel Milvus.
Rappel sémantique des échanges passés.
Phase 2 - Étape 2.4
"""

import time
import hashlib
from typing import List, Dict, Any, Optional
import structlog
from pymilvus import (
    connections, Collection, CollectionSchema,
    FieldSchema, DataType, utility,
)
from rag.embeddings import EmbeddingModel, EMBEDDING_DIM
from config import config

logger = structlog.get_logger(__name__)

MEMORY_COLLECTION = "alexsys_memory"


class LongTermMemory:
    """
    Mémoire long-terme basée sur Milvus.
    Stocke et retrouve les échanges passés par similarité sémantique.
    """

    def __init__(self):
        self.embedding_model = EmbeddingModel()
        self.collection: Optional[Collection] = None
        self._connect()

    def _connect(self):
        """Connexion Milvus + chargement collection."""
        connections.connect(
            alias="default",
            host=config.MILVUS_HOST,
            port=config.MILVUS_PORT,
        )
        if utility.has_collection(MEMORY_COLLECTION):
            self.collection = Collection(MEMORY_COLLECTION)
            self.collection.load()
            logger.info("Memory collection chargée", name=MEMORY_COLLECTION)
        else:
            self._create_collection()

    def _create_collection(self):
        """Crée la collection mémoire dans Milvus."""
        fields = [
            FieldSchema("memory_id", DataType.VARCHAR, max_length=64,
                       is_primary=True, auto_id=False),
            FieldSchema("embedding", DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
            FieldSchema("query", DataType.VARCHAR, max_length=1024),
            FieldSchema("response", DataType.VARCHAR, max_length=4096),
            FieldSchema("session_id", DataType.VARCHAR, max_length=128),
            FieldSchema("timestamp", DataType.DOUBLE),
        ]
        schema = CollectionSchema(fields, description="Agent long-term memory")
        self.collection = Collection(MEMORY_COLLECTION, schema=schema)
        self.collection.create_index(
            "embedding",
            {
                "metric_type": "COSINE",
                "index_type": "HNSW",
                "params": {"M": 8, "efConstruction": 64},
            }
        )
        self.collection.load()
        logger.info("Memory collection créée", name=MEMORY_COLLECTION)

    def store(
        self,
        query: str,
        response: str,
        session_id: str = "default",
    ) -> str:
        """
        Stocke un échange en mémoire long-terme.
        Returns: memory_id généré
        """
        memory_id = hashlib.md5(
            f"{session_id}_{time.time()}_{query[:20]}".encode()
        ).hexdigest()[:12]

        # Embedding du texte combiné query + response
        combined = f"Q: {query} A: {response[:200]}"
        embedding = self.embedding_model.encode_single(combined)

        self.collection.insert([
            [memory_id],
            [embedding],
            [query[:1000]],
            [response[:4000]],
            [session_id],
            [time.time()],
        ])
        self.collection.flush()

        logger.debug("Mémoire stockée", memory_id=memory_id, session=session_id)
        return memory_id

    def recall(
        self,
        query: str,
        top_k: int = 3,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rappelle les souvenirs les plus pertinents pour une query.
        """
        if self.collection.num_entities == 0:
            return []

        query_embedding = self.embedding_model.encode_single(query)

        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"ef": 32}},
            limit=top_k,
            output_fields=["query", "response", "session_id", "timestamp"],
        )

        memories = []
        for hit in results[0]:
            memories.append({
                "memory_id": hit.id,
                "query": hit.entity.get("query"),
                "response": hit.entity.get("response"),
                "session_id": hit.entity.get("session_id"),
                "similarity": float(hit.score),
            })

        logger.debug("Recall", query=query[:50], memories=len(memories))
        return memories

    def format_memories_as_context(self, memories: List[Dict]) -> str:
        """Formate les souvenirs comme contexte pour le LLM."""
        if not memories:
            return ""
        parts = ["[Mémoire conversationnelle pertinente]"]
        for m in memories:
            parts.append(f"Q: {m['query']}\nA: {m['response'][:200]}...")
        return "\n\n".join(parts)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "collection": MEMORY_COLLECTION,
            "total_memories": self.collection.num_entities,
        }