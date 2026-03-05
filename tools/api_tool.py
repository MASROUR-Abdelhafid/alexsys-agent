"""
Outil API externe simulée.
Phase 2 - Étape 2.3
"""

import time
import random
from typing import Dict, Any
import structlog

logger = structlog.get_logger(__name__)


def call_external_api(
    endpoint: str,
    params: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Simule un appel API externe.
    Endpoints disponibles : /clients, /stats, /contracts
    """
    t_start = time.time()
    params = params or {}

    # Simulation latence réseau
    time.sleep(random.uniform(0.05, 0.15))

    mock_responses = {
        "/clients": {
            "status": "success",
            "data": [
                {"id": "C001", "name": "TechCorp SA", "tier": "Premium", "ca": 75000},
                {"id": "C002", "name": "DataSoft", "tier": "Standard", "ca": 25000},
                {"id": "C003", "name": "InnovateLab", "tier": "Premium", "ca": 92000},
            ],
            "total": 3,
        },
        "/stats": {
            "status": "success",
            "data": {
                "churn_rate": 3.2,
                "csat_score": 4.6,
                "nps": 52,
                "active_clients": 147,
                "premium_clients": 38,
            },
        },
        "/contracts": {
            "status": "success",
            "data": [
                {"id": "CTR001", "client": "TechCorp SA", "value": 75000, "renewal": "2026-06-01"},
                {"id": "CTR002", "client": "InnovateLab", "value": 92000, "renewal": "2026-09-15"},
            ],
        },
    }

    response = mock_responses.get(endpoint, {
        "status": "error",
        "message": f"Endpoint inconnu : {endpoint}",
    })

    latency = round((time.time() - t_start) * 1000, 2)
    logger.info("API call", endpoint=endpoint, latency_ms=latency)

    return {
        "tool": "api_call",
        "endpoint": endpoint,
        "result": response,
        "latency_ms": latency,
    }