"""Tests Vector Store Milvus."""
import pytest
from rag.vector_store import MilvusVectorStore
from rag.ingestion import DocumentIngestionPipeline


def test_dense_search_returns_results():
    store = MilvusVectorStore()
    results = store.dense_search("clients Premium SLA", top_k=5)
    assert len(results) > 0
    assert all("content" in r for r in results)
    assert all("score" in r for r in results)
    print(f"\n✅ {len(results)} résultats retournés")
    print(f"   Top score : {results[0]['score']:.4f}")
    print(f"   Contenu   : {results[0]['content'][:80]}...")


def test_scores_between_0_and_1():
    store = MilvusVectorStore()
    results = store.dense_search("sécurité RGPD chiffrement", top_k=5)
    for r in results:
        assert 0.0 <= r["score"] <= 1.0, f"Score invalide : {r['score']}"
    print(f"\n✅ Tous les scores sont dans [0, 1]")


def test_collection_stats():
    store = MilvusVectorStore()
    stats = store.get_collection_stats()
    assert stats["num_entities"] > 0
    assert stats["embedding_dim"] == 384
    print(f"\n✅ Stats collection : {stats}")


if __name__ == "__main__":
    test_dense_search_returns_results()
    test_scores_between_0_and_1()
    test_collection_stats()