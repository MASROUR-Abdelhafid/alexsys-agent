"""Tests du pipeline d'ingestion."""

import pytest
from rag.ingestion import DocumentIngestionPipeline, IngestionConfig


def test_ingestion_basic():
    """Test ingestion fichier texte de base."""
    pipeline = DocumentIngestionPipeline()
    chunks = pipeline.ingest("data/sample/alexsys_knowledge_base.txt")

    assert len(chunks) > 0, "Aucun chunk produit"
    print(f"\n✅ Nombre de chunks : {len(chunks)}")
    print(f"✅ Premier chunk (extrait) : {chunks[0]['content'][:100]}...")
    print(f"✅ Métadonnées : {chunks[0]['metadata']}")


def test_chunk_size():
    """Vérifie que les chunks respectent la taille max."""
    config = IngestionConfig(chunk_size=512, chunk_overlap=64)
    pipeline = DocumentIngestionPipeline(config)
    chunks = pipeline.ingest("data/sample/alexsys_knowledge_base.txt")

    oversized = [
        c for c in chunks
        if c["metadata"]["char_count"] > config.chunk_size * 1.2
    ]
    print(f"\n✅ Chunks hors taille : {len(oversized)}/{len(chunks)}")
    assert len(oversized) == 0, f"{len(oversized)} chunks trop grands"


def test_chunk_ids_unique():
    """Vérifie l'unicité des chunk IDs."""
    pipeline = DocumentIngestionPipeline()
    chunks = pipeline.ingest("data/sample/alexsys_knowledge_base.txt")

    ids = [c["metadata"]["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids)), "IDs dupliqués détectés"
    print(f"\n✅ Tous les {len(ids)} chunk IDs sont uniques")


def test_chunk_stats():
    """Affiche les statistiques du chunking."""
    pipeline = DocumentIngestionPipeline()
    chunks = pipeline.ingest("data/sample/alexsys_knowledge_base.txt")

    sizes = [c["metadata"]["char_count"] for c in chunks]
    print(f"\n📊 Statistiques chunking :")
    print(f"   Total chunks    : {len(chunks)}")
    print(f"   Taille min      : {min(sizes)} chars")
    print(f"   Taille max      : {max(sizes)} chars")
    print(f"   Taille moyenne  : {sum(sizes)//len(sizes)} chars")

    sections = [
        c["metadata"]["section"] for c in chunks
        if c["metadata"]["section"]
    ]
    print(f"   Sections détectées : {len(set(sections))}")
    for s in set(sections):
        print(f"      → {s}")


if __name__ == "__main__":
    test_ingestion_basic()
    test_chunk_size()
    test_chunk_ids_unique()
    test_chunk_stats()