"""Tests Re-ranking Cross-Encoder + RAG Pipeline complet."""

import pytest
from rag.reranker import CrossEncoderReranker
from rag.rag_pipeline import RAGPipeline


def test_reranker_changes_order():
    """Le re-ranker doit modifier l'ordre des candidats."""
    reranker = CrossEncoderReranker()

    # Candidats simulés
    candidates = [
        {"chunk_id": "a1", "content": "Redis cache TTL 3600 secondes système.", "score": 0.9, "retrieval_type": "dense", "source": "doc1", "chunk_index": 0, "section": ""},
        {"chunk_id": "a2", "content": "Les clients Premium bénéficient d'un SLA de 4 heures et account manager dédié.", "score": 0.7, "retrieval_type": "dense", "source": "doc1", "chunk_index": 1, "section": ""},
        {"chunk_id": "a3", "content": "Taux de churn acceptable inférieur à 5% par trimestre.", "score": 0.5, "retrieval_type": "sparse", "source": "doc1", "chunk_index": 2, "section": ""},
    ]

    query = "SLA clients Premium account manager"
    results = reranker.rerank(query=query, candidates=candidates, top_k=3)

    assert len(results) == 3
    assert results[0]["chunk_id"] == "a2", "a2 doit être premier (plus pertinent pour la query)"
    print(f"\n✅ Re-ranking a modifié l'ordre correctement")
    for r in results:
        print(f"   Rank {r['final_rank']}: score={r['cross_encoder_score']:.4f} | {r['content'][:60]}...")


def test_reranker_scores_sorted():
    """Cross-encoder scores doivent être triés décroissants."""
    reranker = CrossEncoderReranker()
    candidates = [
        {"chunk_id": f"c{i}", "content": f"Document {i} contenu texte exemple alexsys.", "score": 0.5, "retrieval_type": "dense", "source": "doc", "chunk_index": i, "section": ""}
        for i in range(5)
    ]
    results = reranker.rerank("clients contrats", candidates, top_k=5)
    scores = [r["cross_encoder_score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    print(f"\n✅ Scores triés: {[f'{s:.3f}' for s in scores]}")


def test_rag_pipeline_full():
    """Test pipeline RAG complet end-to-end."""
    pipeline = RAGPipeline(hybrid_candidates=8, rerank_top_k=3)
    pipeline.build_index()

    result = pipeline.retrieve("Quel est le SLA pour les clients Premium ?", top_k=3)

    assert "chunks" in result
    assert "context" in result
    assert "metadata" in result
    assert len(result["chunks"]) > 0
    assert len(result["context"]) > 0

    print(f"\n✅ Pipeline RAG complet")
    print(f"   Latence totale  : {result['metadata']['total_latency_ms']} ms")
    print(f"   Latence hybrid  : {result['metadata']['hybrid_latency_ms']} ms")
    print(f"   Latence rerank  : {result['metadata']['rerank_latency_ms']} ms")
    print(f"   Top CE score    : {result['metadata']['top_cross_encoder_score']:.4f}")
    print(f"\n   CONTEXTE GÉNÉRÉ :")
    print(f"   {result['context'][:300]}...")


def test_rag_pipeline_context_format():
    """Vérifie le format du contexte généré."""
    pipeline = RAGPipeline(hybrid_candidates=8, rerank_top_k=3)
    pipeline.build_index()

    result = pipeline.retrieve("politique sécurité RGPD", top_k=3)
    context = result["context"]

    assert "[Source 1" in context  # accepte [Source 1] ou [Source 1 [section]]
    assert "---" in context
    print(f"\n✅ Format contexte correct")
    print(f"   Longueur contexte: {len(context)} chars")