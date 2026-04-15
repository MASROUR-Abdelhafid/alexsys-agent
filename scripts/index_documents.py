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

    config_ing = IngestionConfig(chunk_size=600, chunk_overlap=80, min_chunk_size=50)
    pipeline = DocumentIngestionPipeline(config_ing)

    all_chunks = []

    # 1. PDF principal
    print("\n📄 Étape 1/4 : Ingestion du PDF procédés...")
    pdf_path = "data/acierie/Description_du_processus_acierie.pdf"
    if not os.path.exists(pdf_path):
        pdf_path = "data/acierie/Description_du_processus_aciérie.pdf"

    if os.path.exists(pdf_path):
        chunks_pdf = pipeline.ingest(pdf_path)
        all_chunks.extend(chunks_pdf)
        print(f"   ✅ {len(chunks_pdf)} chunks depuis PDF")
    else:
        print("   ⚠️  PDF introuvable")

    # 2. Descriptions schémas/images
    print("\n📄 Étape 2/4 : Ingestion descriptions schémas...")
    schemas_path = "data/acierie/schemas_description.txt"
    if os.path.exists(schemas_path):
        chunks_schemas = pipeline.ingest(schemas_path)
        all_chunks.extend(chunks_schemas)
        print(f"   ✅ {len(chunks_schemas)} chunks depuis schémas")
    else:
        print("   ⚠️  Fichier schémas introuvable")

    print(f"\n   📊 Total chunks : {len(all_chunks)}")

    # 3. Connexion Milvus
    print("\n🗄️  Étape 3/4 : Initialisation Milvus...")
    store = MilvusVectorStore()
    store.create_collection(drop_if_exists=True)
    stats = store.get_collection_stats()
    print(f"   ✅ Collection '{stats['name']}' prête")

    # 4. Indexation
    print("\n⚡ Étape 4/4 : Génération embeddings + insertion...")
    inserted = store.insert_chunks(all_chunks)
    print(f"   ✅ {inserted} chunks indexés dans Milvus")

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
        "schéma procédé aciérie",
        "capacité parc ferraille",
    ]
    for q in queries:
        results = store.dense_search(q, top_k=2)
        print(f"\n   Q: '{q}'")
        for r in results:
            print(f"   Score: {r['score']:.4f} | {r['content'][:70]}...")

    print("\n✅ INDEXATION COMPLÈTE !")


if __name__ == "__main__":
    main()