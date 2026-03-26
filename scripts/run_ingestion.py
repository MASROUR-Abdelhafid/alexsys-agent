import os
import sys
import glob

# Ajout du path global
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.ingestion import DataIngestor
from dotenv import load_dotenv

def run():
    print("\n" + "="*60)
    print("🚀 DÉMARRAGE DE L'INGESTION DOCUMENTAIRE (ETL)")
    print("="*60 + "\n")
    
    load_dotenv()
    
    # Recherche dynamique du PDF pour éviter les soucis d'espaces/underscores dans le nom du fichier
    pdf_pattern = os.path.join("data", "acierie", "Description*.pdf")
    pdf_files = glob.glob(pdf_pattern)
    
    if not pdf_files:
        print("❌ ERREUR : Aucun fichier PDF trouvé dans data/acierie/")
        sys.exit(1)
        
    pdf_path = pdf_files[0]
    
    host = os.getenv("MILVUS_HOST", "localhost")
    port = os.getenv("MILVUS_PORT", "19530")
    
    try:
        ingestor = DataIngestor(pdf_path=pdf_path, milvus_host=host, milvus_port=port)
        ingestor.ingest()
    except Exception as e:
        print(f"\n❌ Une erreur est survenue lors de l'ingestion : {str(e)}")

if __name__ == "__main__":
    run()