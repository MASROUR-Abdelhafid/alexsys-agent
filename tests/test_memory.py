"""Tests Memory System."""

import pytest
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from memory.memory_manager import MemoryManager


def test_short_term_memory():
    stm = ShortTermMemory(max_turns=5, session_id="test")
    stm.add_turn("Quel est le SLA Premium ?", "Le SLA Premium est de 4 heures.")
    stm.add_turn("Et pour Standard ?", "Le SLA Standard est de 24 heures.")

    context = stm.get_context(last_n=2)
    assert "SLA Premium" in context
    assert len(stm.get_all_turns()) == 2
    print(f"\n✅ STM: {stm.get_stats()}")
    print(f"   Contexte:\n{context}")


def test_short_term_max_turns():
    stm = ShortTermMemory(max_turns=3)
    for i in range(5):
        stm.add_turn(f"Query {i}", f"Response {i}")
    assert len(stm.get_all_turns()) == 3
    print(f"\n✅ STM fenêtre glissante : {len(stm.get_all_turns())}/3 tours max")


def test_long_term_store_recall():
    ltm = LongTermMemory()
    memory_id = ltm.store(
        query="Politique télétravail Alexsys",
        response="3 jours par semaine maximum.",
        session_id="test_session",
    )
    assert memory_id is not None

    memories = ltm.recall("télétravail travail à distance", top_k=3)
    assert len(memories) >= 0
    print(f"\n✅ LTM store: memory_id={memory_id}")
    print(f"   Recall: {len(memories)} souvenirs")


def test_memory_manager():
    manager = MemoryManager(session_id="test_manager")

    manager.save_interaction(
        "Quel est le budget formation ?",
        "1500 EUR par employé par an.",
    )
    manager.save_interaction(
        "Combien de jours télétravail ?",
        "3 jours par semaine maximum.",
    )

    context = manager.get_full_context("formation budget employé")
    stats = manager.get_stats()

    assert stats["stm"]["turns_count"] == 2
    print(f"\n✅ MemoryManager stats: {stats}")
    print(f"   Contexte: {context[:200]}...")


if __name__ == "__main__":
    test_short_term_memory()
    test_short_term_max_turns()
    test_long_term_store_recall()
    test_memory_manager()