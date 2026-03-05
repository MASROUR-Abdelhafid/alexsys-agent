"""
Mémoire Court-terme — Buffer de conversation.
Fenêtre glissante des N derniers échanges.
Phase 2 - Étape 2.4
"""

import json
import time
from typing import List, Dict, Any, Optional
from collections import deque
import structlog

logger = structlog.get_logger(__name__)


class ShortTermMemory:
    """
    Buffer de conversation en mémoire vive.
    Fenêtre glissante : conserve les N derniers échanges.
    """

    def __init__(self, max_turns: int = 10, session_id: str = "default"):
        self.max_turns = max_turns
        self.session_id = session_id
        self.buffer: deque = deque(maxlen=max_turns)
        self.created_at = time.time()
        logger.info(
            "ShortTermMemory initialisée",
            max_turns=max_turns,
            session_id=session_id,
        )

    def add_turn(
        self,
        query: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Ajoute un échange query/response au buffer."""
        turn = {
            "turn_id": len(self.buffer) + 1,
            "timestamp": time.time(),
            "query": query,
            "response": response,
            "metadata": metadata or {},
        }
        self.buffer.append(turn)
        logger.debug(
            "Tour ajouté à la mémoire",
            turn_id=turn["turn_id"],
            session=self.session_id,
        )

    def get_context(self, last_n: int = 3) -> str:
        """
        Retourne les N derniers échanges formatés
        comme contexte pour le LLM.
        """
        turns = list(self.buffer)[-last_n:]
        if not turns:
            return ""

        parts = []
        for t in turns:
            parts.append(f"User: {t['query']}\nAssistant: {t['response']}")

        return "\n\n".join(parts)

    def get_all_turns(self) -> List[Dict[str, Any]]:
        """Retourne tous les tours du buffer."""
        return list(self.buffer)

    def clear(self):
        """Vide le buffer."""
        self.buffer.clear()
        logger.info("ShortTermMemory vidée", session=self.session_id)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turns_count": len(self.buffer),
            "max_turns": self.max_turns,
            "age_seconds": round(time.time() - self.created_at, 1),
        }