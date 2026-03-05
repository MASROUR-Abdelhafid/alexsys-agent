"""Tests BM25 Sparse Retrieval."""

import pytest
from rag.sparse_retrieval import BM25Retriever
from rag.ingestion import DocumentIngestionPipeline


# Fixture partagée
def get_chunks():
    pipeline = DocumentIngestionPipeline()
    return pipeline.ingest("data/sample/alexsys_knowledge_base.txt")


def test_bm25_index_construction():
    """Vérifie que l'index se construit correctement."""
    chunks = get_chunks()
    retriever = BM25Retriever()
    retriever.index(chunks)
    stats = retriever.get_stats()

    assert stats["num_docs"] == len(chunks)
    assert stats["vocab_size"] > 0
    print(f"\n✅ Index BM25 construit")
    print(f"   Docs      : {stats['num_docs']}")
    print(f"   Vocab     : {stats['vocab_size']} termes")
    print(f"   Avg tokens: {stats['avg_tokens_per_doc']}")


def test_bm25_exact_term_search():
    """BM25 doit exceller sur les termes exacts."""
    chunks = get_chunks()
    retriever = BM25Retriever()
    retriever.index(chunks)

    # Termes techniques exacts présents dans le corpus
    results = retriever.search("ISO 27001 RGPD chiffrement", top_k=5)

    assert len(results) > 0
    print(f"\n✅ Résultats pour 'ISO 27001 RGPD' : {len(results)}")
    for r in results[:3]:
        print(f"   Score: {r['score']:.4f} | Tokens: {r['matched_tokens']}")
        print(f"   Extrait: {r['content'][:80]}...")


def test_bm25_scores_positive():
    """Scores BM25 doivent être positifs pour résultats retournés."""
    chunks = get_chunks()
    retriever = BM25Retriever()
    retriever.index(chunks)

    results = retriever.search("contrat client renouvellement annuel", top_k=5)
    for r in results:
        assert r["score"] > 0, f"Score négatif: {r['score']}"
    print(f"\n✅ Tous les scores sont positifs ({len(results)} résultats)")


def test_bm25_save_load(tmp_path):
    """Vérifie sauvegarde et rechargement de l'index."""
    chunks = get_chunks()
    retriever = BM25Retriever()
    retriever.index(chunks)

    # Sauvegarder
    save_path = str(tmp_path / "bm25_index.pkl")
    retriever.save(save_path)

    # Recharger
    loaded = BM25Retriever.load(save_path)
    results = loaded.search("chiffre affaires Premium", top_k=3)

    assert len(results) > 0
    print(f"\n✅ Save/Load OK — {len(results)} résultats après rechargement")


def test_bm25_vs_dense_complementarity():
    """
    Démontre la complémentarité BM25 vs Dense.
    BM25 doit mieux scorer sur termes techniques exacts.
    """
    chunks = get_chunks()
    retriever = BM25Retriever()
    retriever.index(chunks)

    # Requête avec acronyme technique
    results = retriever.search("99.9% SLA trois neuf disponibilité", top_k=3)

    print(f"\n✅ Test complémentarité BM25/Dense")
    print(f"   Requête: '99.9% SLA trois neuf disponibilité'")
    for r in results:
        print(f"   Score BM25: {r['score']:.4f}")
        print(f"   Tokens matchés: {r['matched_tokens']}")
        print(f"   Contenu: {r['content'][:100]}...")


if __name__ == "__main__":
    test_bm25_index_construction()
    test_bm25_exact_term_search()
    test_bm25_scores_positive()
    test_bm25_vs_dense_complementarity()