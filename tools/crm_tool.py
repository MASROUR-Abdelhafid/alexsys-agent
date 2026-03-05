"""
Outil CRM Mock.
Phase 2 - Étape 2.3
"""

import time
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)

# CRM en mémoire
CRM_DATA = {
    "C001": {
        "crm_id": "C001", "company": "TechCorp SA",
        "contact": "Jean Dubois", "email": "j.dubois@techcorp.fr",
        "tier": "Premium", "health_score": 87,
        "last_contact": "2026-02-28", "next_renewal": "2026-06-01",
        "tags": ["api-integration", "high-value"],
    },
    "C002": {
        "crm_id": "C002", "company": "DataSoft",
        "contact": "Marie Leroy", "email": "m.leroy@datasoft.fr",
        "tier": "Standard", "health_score": 72,
        "last_contact": "2026-02-15", "next_renewal": "2026-08-20",
        "tags": ["at-risk"],
    },
    "C003": {
        "crm_id": "C003", "company": "InnovateLab",
        "contact": "Pierre Martin", "email": "p.martin@innovatelab.fr",
        "tier": "Premium", "health_score": 94,
        "last_contact": "2026-03-01", "next_renewal": "2026-09-15",
        "tags": ["champion", "expansion-candidate"],
    },
}


def crm_lookup(
    client_id: Optional[str] = None,
    company_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Recherche dans le CRM par ID ou nom d'entreprise.
    """
    t_start = time.time()

    if client_id and client_id in CRM_DATA:
        result = CRM_DATA[client_id]
    elif company_name:
        result = next(
            (c for c in CRM_DATA.values()
             if company_name.lower() in c["company"].lower()),
            None,
        )
    else:
        result = list(CRM_DATA.values())

    latency = round((time.time() - t_start) * 1000, 2)
    logger.info("CRM lookup", client_id=client_id, latency_ms=latency)

    return {
        "tool": "crm_lookup",
        "result": result,
        "latency_ms": latency,
    }


def get_at_risk_clients() -> Dict[str, Any]:
    """Retourne les clients à risque (health_score < 75)."""
    at_risk = [
        c for c in CRM_DATA.values()
        if c["health_score"] < 75
    ]
    return {"tool": "crm_lookup", "result": at_risk, "count": len(at_risk)}