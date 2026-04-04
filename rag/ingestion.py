"""
Module d'ingestion et chunking de documents.
Phase 1 - Étape 1.1
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

# from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_core.documents import Document
try:
    from langchain_community.document_loaders import TextLoader, PyPDFLoader, DirectoryLoader
except ImportError:
    from langchain.document_loaders import TextLoader, PyPDFLoader, DirectoryLoader

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ChunkMetadata:
    """Métadonnées associées à chaque chunk."""
    source: str
    chunk_id: str
    chunk_index: int
    total_chunks: int
    char_count: int
    word_count: int
    section: Optional[str] = None


@dataclass
class IngestionConfig:
    """Configuration du pipeline d'ingestion."""
    chunk_size: int = 512
    chunk_overlap: int = 64
    min_chunk_size: int = 50
    separators: List[str] = field(default_factory=lambda: [
        "\n=== ", "\n\n", "\n", ". ", " ", ""
    ])


class DocumentIngestionPipeline:
    """
    Pipeline d'ingestion et chunking de documents.
    
    Stratégie : Recursive Character Text Splitter avec overlap
    pour préserver la cohérence sémantique inter-chunks.
    """

    def __init__(self, config: Optional[IngestionConfig] = None):
        self.config = config or IngestionConfig()
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            length_function=len,
            separators=self.config.separators,
        )
        logger.info(
            "Pipeline d'ingestion initialisé",
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )

    def _generate_chunk_id(self, content: str, source: str, index: int) -> str:
        """Génère un identifiant unique et reproductible pour chaque chunk."""
        raw = f"{source}_{index}_{content[:50]}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def _extract_section(self, content: str) -> Optional[str]:
        """Extrait le titre de section si présent."""
        lines = content.strip().split("\n")
        for line in lines[:3]:
            if line.startswith("===") or line.startswith("#"):
                return line.strip("= #").strip()
        return None

    def _clean_text(self, text: str) -> str:
        """Nettoyage basique du texte."""
        # Supprimer espaces multiples
        import re
        text = re.sub(r' +', ' ', text)
        # Normaliser sauts de ligne
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def load_file(self, file_path: str) -> List[Document]:
        """Charge un fichier selon son extension."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Fichier introuvable : {file_path}")

        ext = path.suffix.lower()

        if ext == ".txt":
            loader = TextLoader(str(path), encoding="utf-8")
        elif ext == ".pdf":
            loader = PyPDFLoader(str(path))
        else:
            raise ValueError(f"Extension non supportée : {ext}")

        docs = loader.load()
        logger.info("Fichier chargé", path=str(path), pages=len(docs))
        return docs

    def load_directory(self, dir_path: str, glob: str = "**/*.txt") -> List[Document]:
        """Charge tous les documents d'un répertoire."""
        loader = DirectoryLoader(
            dir_path,
            glob=glob,
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
            show_progress=True,
        )
        docs = loader.load()
        logger.info("Répertoire chargé", path=dir_path, documents=len(docs))
        return docs

    def chunk_documents(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """
        Découpe les documents en chunks avec métadonnées enrichies.
        
        Returns:
            Liste de dicts {content, metadata} prêts pour l'indexation.
        """
        all_chunks = []

        for doc in documents:
            # Nettoyage
            clean_content = self._clean_text(doc.page_content)
            source = doc.metadata.get("source", "unknown")

            # Chunking
            raw_chunks = self.splitter.split_text(clean_content)

            # Filtrage chunks trop petits
            raw_chunks = [
                c for c in raw_chunks
                if len(c.strip()) >= self.config.min_chunk_size
            ]

            total = len(raw_chunks)

            for idx, chunk_text in enumerate(raw_chunks):
                chunk_id = self._generate_chunk_id(chunk_text, source, idx)
                section = self._extract_section(chunk_text)

                chunk = {
                    "content": chunk_text.strip(),
                    "metadata": {
                        "source": source,
                        "chunk_id": chunk_id,
                        "chunk_index": idx,
                        "total_chunks": total,
                        "char_count": len(chunk_text),
                        "word_count": len(chunk_text.split()),
                        "section": section,
                    }
                }
                all_chunks.append(chunk)

        logger.info(
            "Chunking terminé",
            total_documents=len(documents),
            total_chunks=len(all_chunks),
            avg_chunk_size=sum(
                c["metadata"]["char_count"] for c in all_chunks
            ) // max(len(all_chunks), 1),
        )

        return all_chunks

    def ingest(self, source: str) -> List[Dict[str, Any]]:
        """
        Point d'entrée principal du pipeline.
        
        Args:
            source: chemin vers un fichier ou répertoire
            
        Returns:
            Liste de chunks prêts pour l'indexation
        """
        path = Path(source)

        if path.is_dir():
            documents = self.load_directory(str(path))
        else:
            documents = self.load_file(str(path))

        return self.chunk_documents(documents)