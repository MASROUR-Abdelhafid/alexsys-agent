"""
Module d'ingestion documentaire (ETL pour RAG).
Charge le PDF, applique le chunking, et peuple Milvus (Dense) et BM25 (Sparse).
"""

import os
import pickle
import structlog
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Milvus
from langchain_community.embeddings import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi

logger = structlog.get_logger(__name__)

class DataIngestor:
    def __init__(self, pdf_path: str, milvus_host: str = "localhost", milvus_port: str = "19530"):
        self.pdf_path = pdf_path
        self.milvus_uri = f"http://{milvus_host}:{milvus_port}"
        
        logger.info("Initialisation du modèle d'embeddings (cela peut prendre quelques secondes)...")
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.collection_name = "acierie_docs"
        
        # Dossier pour stocker l'index local BM25 et les chunks bruts
        self.index_dir = os.path.join("data", "index")
        os.makedirs(self.index_dir, exist_ok=True)
        self.bm25_path = os.path.join(self.index_dir, "bm25_model.pkl")
        self.chunks_path = os.path.join(self.index_dir, "chunks_data.pkl")

    def ingest(self):
        logger.info("Démarrage de l'ingestion PDF...", fichier=self.pdf_path)
        
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"Le fichier {self.pdf_path} est introuvable. Vérifie le chemin.")
            
        # 1. Parsing du PDF
        loader = PyPDFLoader(self.pdf_path)
        docs = loader.load()
        logger.info("PDF chargé avec succès.", nb_pages=len(docs))
        
        # 2. Chunking (Sémantique)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, 
            chunk_overlap=150,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        chunks = text_splitter.split_documents(docs)
        logger.info("Découpage en chunks terminé.", nb_chunks=len(chunks))
        
        # 3. Dense Retrieval (Injection dans Milvus)
        logger.info("Génération des vecteurs et insertion dans Milvus...", uri=self.milvus_uri)
        Milvus.from_documents(
            chunks,
            self.embeddings,
            connection_args={"uri": self.milvus_uri},
            collection_name=self.collection_name,
            drop_old=True # Sécurité : écrase l'ancienne collection si on relance le script
        )
        logger.info("Insertion Milvus (Dense) réussie.")
        
        # 4. Sparse Retrieval (Création index BM25 local)
        logger.info("Création de l'index BM25...")
        # On tokenise le texte (mise en minuscules et séparation par mots)
        tokenized_corpus = [chunk.page_content.lower().split(" ") for chunk in chunks]
        bm25 = BM25Okapi(tokenized_corpus)
        
        # Sauvegarde physique pour que le RetrieverAgent puisse s'en servir plus tard
        with open(self.bm25_path, "wb") as f:
            pickle.dump(bm25, f)
        with open(self.chunks_path, "wb") as f:
            pickle.dump(chunks, f)
            
        logger.info("Index BM25 (Sparse) sauvegardé localement.")
        logger.info("✅ PROCESSUS D'INGESTION TERMINÉ AVEC SUCCÈS.")