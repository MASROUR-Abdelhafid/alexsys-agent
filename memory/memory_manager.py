"""
Memory Manager — Coordonne Short-term et Long-term memory.
Phase 2 - Étape 2.4
"""

from typing import Dict, Any, Optional
import structlog

from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory

logger = structlog.get_logger(__name__)


class MemoryManager:
    """
    Gestionnaire unifié de mémoire.
    Coordonne STM (buffer) et LTM (Milvus).
    """

    def __init__(self, session_id: str = "default", max_turns: int = 10):
        self.session_id = session_id
        self.stm = ShortTermMemory(max_turns=max_turns, session_id=session_id)
        self.ltm = LongTermMemory()
        logger.info("MemoryManager initialisé", session_id=session_id)

    def save_interaction(self, query: str, response: str, metadata: Dict = None):
        """Sauvegarde un échange dans STM et LTM."""
        self.stm.add_turn(query, response, metadata)
        self.ltm.store(query, response, self.session_id)
        logger.debug("Interaction sauvegardée", session=self.session_id)

    def get_full_context(self, query: str) -> str:
        """
        Construit le contexte mémoire complet :
        STM (3 derniers tours) + LTM (3 souvenirs pertinents).
        """
        stm_context = self.stm.get_context(last_n=3)
        memories = self.ltm.recall(query, top_k=3, session_id=self.session_id)
        ltm_context = self.ltm.format_memories_as_context(memories)

        parts = []
        if stm_context:
            parts.append(f"[Conversation récente]\n{stm_context}")
        if ltm_context:
            parts.append(ltm_context)

        return "\n\n".join(parts)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "stm": self.stm.get_stats(),
            "ltm": self.ltm.get_stats(),
        }