"""
Script d'indexation : ingestion → embeddings → Milvus.
Usage : python scripts/index_documents.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.ingestion import DocumentIngestionPipeline, IngestionConfig
from rag.vector_store import MilvusVectorStore


def main():
    print("=" * 60)
    print("🚀 PIPELINE D'INDEXATION — ALEXSYS RAG")
    print("=" * 60)

    # 1. Ingestion & chunking
    print("\n📄 Étape 1/3 : Ingestion et chunking...")
    config = IngestionConfig(chunk_size=512, chunk_overlap=64)
    pipeline = DocumentIngestionPipeline(config)
    chunks = pipeline.ingest("data/sample/alexsys_knowledge_base.txt")
    print(f"   ✅ {len(chunks)} chunks produits")

    # 2. Connexion Milvus
    print("\n🗄️  Étape 2/3 : Initialisation Milvus...")
    store = MilvusVectorStore()
    store.create_collection(drop_if_exists=True)
    stats = store.get_collection_stats()
    print(f"   ✅ Collection '{stats['name']}' créée")

    # 3. Insertion
    print("\n⚡ Étape 3/3 : Génération embeddings + insertion...")
    inserted = store.insert_chunks(chunks)
    print(f"   ✅ {inserted} chunks indexés dans Milvus")

    # Résumé
    stats = store.get_collection_stats()
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ INDEXATION")
    print("=" * 60)
    for k, v in stats.items():
        print(f"   {k:<20} : {v}")

    # Test recherche rapide
    print("\n🔍 Test recherche dense...")
    results = store.dense_search("politique clients Premium", top_k=3)
    print(f"   ✅ {len(results)} résultats trouvés")
    for i, r in enumerate(results):
        print(f"\n   [{i+1}] Score: {r['score']:.4f}")
        print(f"       Section: {r['section']}")
        print(f"       Extrait: {r['content'][:100]}...")

    print("\n✅ INDEXATION COMPLÈTE !")


if __name__ == "__main__":
    main()