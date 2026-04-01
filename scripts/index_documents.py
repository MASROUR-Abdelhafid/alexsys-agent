"""
Script d'indexation RAG — PDF Aciérie vers Milvus.
Indexe la documentation technique pour le retriever.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.ingestion import DocumentIngestionPipeline, IngestionConfig
from rag.vector_store import MilvusVectorStore


def main():
    print("=" * 60)
    print("🏭 INDEXATION RAG — DOCUMENTATION ACIÉRIE")
    print("=" * 60)

    # 1. Ingestion PDF
    print("\n📄 Étape 1/3 : Ingestion du PDF...")
    config = IngestionConfig(
        chunk_size=600,
        chunk_overlap=80,
        min_chunk_size=50,
    )
    pipeline = DocumentIngestionPipeline(config)

    pdf_path = "data/acierie/Description_du_processus_acierie.pdf"
    if not os.path.exists(pdf_path):
        # Essayer avec accent
        pdf_path = "data/acierie/Description_du_processus_aciérie.pdf"

    if not os.path.exists(pdf_path):
        print(f"❌ PDF introuvable : {pdf_path}")
        print("   Fichiers disponibles :")
        for f in os.listdir("data/acierie"):
            print(f"   - {f}")
        return

    chunks = pipeline.ingest(pdf_path)
    print(f"   ✅ {len(chunks)} chunks produits depuis le PDF")
    for i, c in enumerate(chunks[:3]):
        print(f"   [{i+1}] {c['content'][:80]}...")

    # 2. Connexion Milvus
    print("\n🗄️  Étape 2/3 : Initialisation Milvus...")
    store = MilvusVectorStore()
    store.create_collection(drop_if_exists=True)
    stats = store.get_collection_stats()
    print(f"   ✅ Collection '{stats['name']}' prête")

    # 3. Indexation
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

    # Test recherche
    print("\n🔍 Test recherche RAG...")
    queries = [
        "comment fonctionne le four EAF",
        "rôle du four poche LF",
        "coulée continue CCM brames",
    ]
    for q in queries:
        results = store.dense_search(q, top_k=2)
        print(f"\n   Q: '{q}'")
        for r in results:
            print(f"   Score: {r['score']:.4f} | {r['content'][:80]}...")

    print("\n✅ INDEXATION COMPLÈTE !")


if __name__ == "__main__":
    main()