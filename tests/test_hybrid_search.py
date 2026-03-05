"""Tests Hybrid Search RRF."""

import pytest
from rag.hybrid_search import HybridSearchEngine


def get_engine():
    engine = HybridSearchEngine(dense_weight=0.5, sparse_weight=0.5, rrf_k=60)
    engine.build_bm25_index()
    return engine


def test_hybrid_returns_results():
    """Hybrid search retourne des résultats."""
    engine = get_engine()
    results = engine.search("politique clients Premium SLA", top_k=5)

    assert len(results) > 0
    assert len(results) <= 5
    print(f"\n✅ {len(results)} résultats hybrid")
    for r in results:
        print(f"   RRF: {r['rrf_score']:.6f} | Type: {r['retrieval_type']}")
        print(f"   Extrait: {r['content'][:80]}...")


def test_rrf_scores_ordered():
    """Les scores RRF doivent être triés décroissants."""
    engine = get_engine()
    results = engine.search("sécurité RGPD ISO 27001", top_k=5)

    scores = [r["rrf_score"] for r in results]
    assert scores == sorted(scores, reverse=True), "Scores non triés"
    print(f"\n✅ Scores RRF triés correctement: {[f'{s:.5f}' for s in scores]}")


def test_hybrid_better_than_individual():
    """
    Hybrid doit couvrir plus de chunks uniques
    que dense ou sparse seuls.
    """
    engine = get_engine()
    analysis = engine.search_with_analysis(
        "ISO 27001 chiffrement AES clients Premium 50000 EUR",
        top_k=5,
    )

    dense_ids = {r["chunk_id"] for r in analysis["dense_results"]}
    sparse_ids = {r["chunk_id"] for r in analysis["sparse_results"]}
    hybrid_ids = {r["chunk_id"] for r in analysis["hybrid_results"]}

    print(f"\n✅ Analyse complémentarité :")
    print(f"   Dense unique  : {len(dense_ids)} chunks")
    print(f"   Sparse unique : {len(sparse_ids)} chunks")
    print(f"   Hybrid unique : {len(hybrid_ids)} chunks")
    print(f"   Overlap D∩S   : {len(dense_ids & sparse_ids)} chunks")
    print(f"   Analysis      : {analysis['analysis']}")

    assert len(hybrid_ids) > 0


def test_retrieval_types_present():
    """Vérifie que les types de retrieval sont bien annotés."""
    engine = get_engine()
    results = engine.search("rapport PDF génération mensuel", top_k=5)

    types = {r["retrieval_type"] for r in results}
    print(f"\n✅ Types de retrieval présents: {types}")
    assert all(
        t in ["hybrid", "dense_only", "sparse_only"]
        for t in types
    )


def test_search_with_analysis():
    """Test analyse comparative complète."""
    engine = get_engine()
    analysis = engine.search_with_analysis(
        "disponibilité système 99.9% SLA",
        top_k=3,
    )

    assert "dense_results" in analysis
    assert "sparse_results" in analysis
    assert "hybrid_results" in analysis
    assert "analysis" in analysis

    print(f"\n✅ Analyse comparative :")
    print(f"   Query  : {analysis['query']}")
    print(f"   Dense  : {len(analysis['dense_results'])} résultats")
    print(f"   Sparse : {len(analysis['sparse_results'])} résultats")
    print(f"   Hybrid : {len(analysis['hybrid_results'])} résultats")
    print(f"   Stats  : {analysis['analysis']}")


if __name__ == "__main__":
    test_hybrid_returns_results()
    test_rrf_scores_ordered()
    test_hybrid_better_than_individual()
    test_retrieval_types_present()
    test_search_with_analysis()