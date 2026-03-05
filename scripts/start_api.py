"""Script lancement API."""
import sys
import os

# Ajouter la racine du projet au PATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["api", "agents", "rag", "tools", "memory"],
        log_level="info",
    )