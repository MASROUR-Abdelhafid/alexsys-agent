import json
import os
from datetime import datetime
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Fichier local servant de base de données pour notre mock CRM
DB_PATH = os.path.join("data", "mock_crm_db.json")

class TicketInput(BaseModel):
    title: str = Field(description="Titre concis de l'incident ou de l'alerte KPI")
    description: str = Field(description="Description détaillée de l'anomalie industrielle détectée")
    priority: str = Field(description="Niveau de criticité: Basse, Moyenne, Haute, Critique")

@tool("create_crm_ticket", args_schema=TicketInput)
def create_crm_ticket(title: str, description: str, priority: str) -> str:
    """Crée un ticket dans le système CRM/GMAO industriel pour signaler une anomalie KPI nécessitant une intervention."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Chargement de la base existante ou initialisation
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r", encoding="utf-8") as f:
            try:
                db = json.load(f)
            except json.JSONDecodeError:
                db = {"tickets": []}
    else:
        db = {"tickets": []}
    
    # Génération de l'ID métier
    ticket_id = f"TKT-ACIERIE-{len(db['tickets']) + 1:04d}"
    
    ticket = {
        "id": ticket_id,
        "title": title,
        "description": description,
        "priority": priority,
        "status": "Ouvert",
        "created_at": datetime.now().isoformat()
    }
    
    db["tickets"].append(ticket)
    
    # Sauvegarde atomique simulée
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)
        
    return f"Succès : Le ticket d'intervention {ticket_id} a été enregistré dans le CRM avec la priorité '{priority}'."