"""
Outil Base de données SQLite.
Phase 2 - Étape 2.3
"""

import sqlite3
import os
import time
from typing import Dict, Any, List
import structlog

logger = structlog.get_logger(__name__)

DB_PATH = "data/alexsys.db"


def init_database():
    """Initialise la base de données avec des données de test."""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,
            name TEXT,
            tier TEXT,
            annual_revenue REAL,
            sla_hours INTEGER,
            account_manager TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY,
            client_id TEXT,
            subject TEXT,
            status TEXT,
            priority TEXT,
            created_at TEXT,
            resolved_at TEXT
        );

        INSERT OR IGNORE INTO clients VALUES
            ('C001','TechCorp SA','Premium',75000,4,'Alice Martin','2023-01-15'),
            ('C002','DataSoft','Standard',25000,24,'Bob Dupont','2023-03-20'),
            ('C003','InnovateLab','Premium',92000,4,'Alice Martin','2022-11-10'),
            ('C004','StartupXYZ','Standard',15000,24,'Bob Dupont','2024-01-05'),
            ('C005','MegaCorp','Premium',120000,4,'Claire Petit','2021-06-30');

        INSERT OR IGNORE INTO tickets VALUES
            ('T001','C001','Problème connexion API','resolved','high','2026-02-01','2026-02-01'),
            ('T002','C003','Rapport non généré','open','medium','2026-03-01',NULL),
            ('T003','C002','Question facturation','resolved','low','2026-02-15','2026-02-16'),
            ('T004','C001','Performance dégradée','open','high','2026-03-03',NULL),
            ('T005','C005','Intégration CRM','resolved','high','2026-01-20','2026-01-21');
    """)

    conn.commit()
    conn.close()
    logger.info("Base de données initialisée", path=DB_PATH)


def query_database(sql: str, params: tuple = ()) -> Dict[str, Any]:
    """
    Exécute une requête SQL sur la base de données.

    Args:
        sql   : requête SQL SELECT
        params: paramètres de la requête

    Returns:
        dict avec résultats et métadonnées
    """
    t_start = time.time()

    # Sécurité : uniquement SELECT
    if not sql.strip().upper().startswith("SELECT"):
        return {
            "tool": "database_query",
            "error": "Seules les requêtes SELECT sont autorisées",
            "result": [],
        }

    # Initialiser DB si nécessaire
    if not os.path.exists(DB_PATH):
        init_database()

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()

        latency = round((time.time() - t_start) * 1000, 2)
        logger.info(
            "DB query exécutée",
            rows=len(rows),
            latency_ms=latency,
        )

        return {
            "tool": "database_query",
            "sql": sql,
            "result": rows,
            "row_count": len(rows),
            "latency_ms": latency,
        }

    except Exception as e:
        logger.error("DB query error", error=str(e))
        return {
            "tool": "database_query",
            "error": str(e),
            "result": [],
        }


def get_premium_clients() -> Dict[str, Any]:
    """Raccourci : récupère tous les clients Premium."""
    return query_database(
        "SELECT * FROM clients WHERE tier = 'Premium' ORDER BY annual_revenue DESC"
    )


def get_open_tickets() -> Dict[str, Any]:
    """Raccourci : récupère les tickets ouverts."""
    return query_database(
        """SELECT t.*, c.name as client_name, c.tier
           FROM tickets t JOIN clients c ON t.client_id = c.id
           WHERE t.status = 'open' ORDER BY t.priority"""
    )