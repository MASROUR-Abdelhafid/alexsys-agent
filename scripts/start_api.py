"""
Script de lancement du serveur local Uvicorn pour l'API.
"""
import uvicorn
import os
import sys

# Ajout du chemin global pour éviter les erreurs d'importation
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def start():
    print("\n" + "="*50)
    print("🚀 DÉMARRAGE DU SERVEUR API FASTAPI")
    print("="*50 + "\n")
    # Lancement sur le port 8000. 'reload=True' permet le rechargement à chaud lors du développement.
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    start()