"""Tests Agent Retriever intégré au graphe."""

import pytest
from agents.retriever import RetrieverAgent
from agents.state import AgentState
from agents.graph import run_agent


def make_state(query: str) -> AgentState:
    return {
        "query": query,
        "plan": ["Récupérer contexte pertinent"],
        "task_type": "retrieval",
        "retrieved_context": "",
        "tool_results": [],
        "action_history": [],
        "final_response": "",
        "metadata": {},
        "iteration_count": 1,
        "errors": [],
    }


def test_retriever_returns_context():
    """RetrieverAgent doit retourner un contexte non vide."""
    agent = RetrieverAgent(hybrid_candidates=8, rerank_top_k=3)
    state = make_state("Quel est le SLA pour les clients Premium ?")
    result = agent.retrieve(state)

    assert result["retrieved_context"] != ""
    assert "[Source 1" in result["retrieved_context"]
    print(f"\n✅ Contexte récupéré ({len(result['retrieved_context'])} chars)")
    print(f"   Extrait: {result['retrieved_context'][:150]}...")


def test_retriever_metadata():
    """Vérifie que les métriques RAG sont bien loggées."""
    agent = RetrieverAgent(hybrid_candidates=8, rerank_top_k=3)
    state = make_state("politique sécurité RGPD")
    result = agent.retrieve(state)

    assert "retriever_latency_ms" in result["metadata"]
    assert "rag_pipeline" in result["metadata"]
    rag_meta = result["metadata"]["rag_pipeline"]
    assert rag_meta["chunks_reranked"] > 0

    print(f"\n✅ Métriques RAG :")
    print(f"   Latence retriever : {result['metadata']['retriever_latency_ms']} ms")
    print(f"   Chunks reranked   : {rag_meta['chunks_reranked']}")
    print(f"   Top CE score      : {rag_meta['top_cross_encoder_score']:.4f}")


def test_retriever_action_history():
    """Vérifie que l'historique d'actions est bien alimenté."""
    agent = RetrieverAgent(hybrid_candidates=8, rerank_top_k=3)
    state = make_state("contrat renouvellement clients")
    result = agent.retrieve(state)

    history = result["action_history"]
    assert len(history) > 0
    assert history[0]["agent"] == "retriever"
    assert history[0]["action"] == "rag_retrieve"
    print(f"\n✅ Action history : {history[0]['action']} — {history[0]['chunks_retrieved']} chunks")


def test_full_pipeline_with_real_retriever():
    """Test end-to-end graphe avec vrai RetrieverAgent."""
    result = run_agent("Quelle est la politique de télétravail chez Alexsys ?")

    assert result["retrieved_context"] != ""
    assert result["final_response"] != ""
    assert result["iteration_count"] >= 1

    print(f"\n✅ Pipeline complet avec RAG réel")
    print(f"   Task type    : {result['task_type']}")
    print(f"   Contexte     : {result['retrieved_context'][:150]}...")
    print(f"   Réponse      : {result['final_response'][:200]}...")
    rag_meta = result.get("metadata", {}).get("rag_pipeline", {})
    print(f"   Latence RAG  : {rag_meta.get('total_latency_ms', 'N/A')} ms")


if __name__ == "__main__":
    test_retriever_returns_context()
    test_retriever_metadata()
    test_retriever_action_history()
    test_full_pipeline_with_real_retriever()