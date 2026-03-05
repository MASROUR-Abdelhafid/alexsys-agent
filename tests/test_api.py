"""Tests API FastAPI."""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print(f"\n✅ Health check: {data}")


def test_query_endpoint():
    response = client.post("/api/v1/query", json={
        "question": "Quel est le SLA pour les clients Premium ?",
        "session_id": "test_session",
    })
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "task_type" in data
    assert "plan" in data
    print(f"\n✅ Query endpoint:")
    print(f"   Task type : {data['task_type']}")
    print(f"   Réponse   : {data['answer'][:150]}...")
    print(f"   Latence   : {data['metadata'].get('total_api_latency_ms')} ms")


def test_memory_endpoint():
    # D'abord faire une query pour créer la session
    client.post("/api/v1/query", json={
        "question": "Politique télétravail ?",
        "session_id": "mem_test",
    })

    response = client.get("/api/v1/memory/mem_test")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "mem_test"
    assert data["stm_turns"] >= 1
    print(f"\n✅ Memory stats: {data}")


def test_clear_memory():
    response = client.delete("/api/v1/memory/mem_test")
    assert response.status_code == 200
    assert response.json()["status"] == "cleared"
    print(f"\n✅ Memory cleared")


if __name__ == "__main__":
    test_health_check()
    test_query_endpoint()
    test_memory_endpoint()
    test_clear_memory()