"""
Pipeline RAG Avancé - Hybrid Search & Re-ranking.
Combine la recherche sémantique (Milvus), la recherche par mots-clés (BM25),
et réordonne les résultats avec un Cross-Encoder.
"""

import os
import pickle
import structlog
from typing import List
from langchain_community.vectorstores import Milvus
from langchain_community.embeddings import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder

logger = structlog.get_logger(__name__)

class RAGPipeline:
    def __init__(self, milvus_host: str = "localhost", milvus_port: str = "19530"):
        self.milvus_uri = f"http://{milvus_host}:{milvus_port}"
        self.collection_name = "acierie_docs"
        
        # 1. Chargement du modèle Dense (Embeddings)
        logger.info("Chargement des Embeddings...")
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # Connexion à Milvus
        self.vector_store = Milvus(
            embedding_function=self.embeddings,
            connection_args={"uri": self.milvus_uri},
            collection_name=self.collection_name
        )
        
        # 2. Chargement du modèle Sparse (BM25) et des chunks bruts
        index_dir = os.path.join("data", "index")
        bm25_path = os.path.join(index_dir, "bm25_model.pkl")
        chunks_path = os.path.join(index_dir, "chunks_data.pkl")
        
        if os.path.exists(bm25_path) and os.path.exists(chunks_path):
            with open(bm25_path, "rb") as f:
                self.bm25 = pickle.load(f)
            with open(chunks_path, "rb") as f:
                self.chunks = pickle.load(f)
            logger.info("Index BM25 chargé avec succès.")
        else:
            logger.warning("Fichiers BM25 introuvables. Lance run_ingestion.py d'abord.")
            self.bm25 = None
            self.chunks = []

        # 3. Chargement du Re-ranker (Modèle juge)
        logger.info("Chargement du Cross-Encoder (Re-ranker)...")
        self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        logger.info("RAG Pipeline prêt.")

    def retrieve(self, query: str, top_k: int = 3) -> str:
        """Exécute la recherche hybride et retourne le contexte formaté."""
        logger.info("Recherche RAG démarrée", query=query)
        candidates = {} # Dictionnaire pour éviter les doublons {texte: document_source}

        # --- A. RECHERCHE DENSE (Milvus) ---
        try:
            dense_results = self.vector_store.similarity_search(query, k=5)
            for doc in dense_results:
                candidates[doc.page_content] = doc
        except Exception as e:
            logger.error("Erreur Milvus", error=str(e))

        # --- B. RECHERCHE SPARSE (BM25) ---
        if self.bm25 and self.chunks:
            tokenized_query = query.lower().split()
            # Récupère les 5 meilleurs documents selon BM25
            sparse_results = self.bm25.get_top_n(tokenized_query, self.chunks, n=5)
            for doc in sparse_results:
                candidates[doc.page_content] = doc

        if not candidates:
            return "Aucune information technique trouvée dans les manuels."

        # --- C. RE-RANKING (Cross-Encoder) ---
        unique_texts = list(candidates.keys())
        
        # On prépare les paires (Question, Paragraphe) pour le modèle juge
        cross_inp = [[query, text] for text in unique_texts]
        
        # Calcul des scores de pertinence
        scores = self.reranker.predict(cross_inp)
        
        # Tri des textes selon le score du Cross-Encoder (ordre décroissant)
        scored_results = list(zip(scores, unique_texts))
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # --- D. FORMATAGE DU CONTEXTE ---
        # On ne garde que les 'top_k' meilleurs résultats
        best_texts = [text for score, text in scored_results[:top_k]]
        
        context_str = "\n\n---\n\n".join(best_texts)
        logger.info("Recherche terminée", nb_documents_finaux=len(best_texts))
        
        return f"[CONTEXTE DOCUMENTAIRE EXTRAIT (Hybrid RAG)]\n{context_str}"