"""
Logging structuré et audit trail.
Persistance dans logs/audit.log
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

os.makedirs("logs", exist_ok=True)

# Audit logger
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

handler = logging.FileHandler("logs/audit.log", encoding="utf-8")
handler.setFormatter(logging.Formatter("%(message)s"))
audit_logger.addHandler(handler)


def log_audit(
    action: str,
    query: str = "",
    task_type: str = "",
    session_id: str = "",
    latency_ms: float = 0,
    kpis: list = None,
    error: str = "",
):
    """Enregistre une entrée d'audit."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "session_id": session_id,
        "query": query[:100],
        "task_type": task_type,
        "latency_ms": latency_ms,
        "kpis_detected": kpis or [],
        "error": error,
    }
    audit_logger.info(json.dumps(entry, ensure_ascii=False))