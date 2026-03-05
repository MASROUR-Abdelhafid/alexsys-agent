"""Tests des outils."""

import os
import pytest
from tools.api_tool import call_external_api
from tools.database_tool import init_database, get_premium_clients, get_open_tickets
from tools.crm_tool import crm_lookup, get_at_risk_clients
from tools.pdf_generator import generate_pdf_report


def test_api_tool():
    result = call_external_api("/clients")
    assert result["result"]["status"] == "success"
    assert len(result["result"]["data"]) > 0
    print(f"\n✅ API tool: {len(result['result']['data'])} clients")


def test_api_stats():
    result = call_external_api("/stats")
    assert "churn_rate" in result["result"]["data"]
    print(f"\n✅ API stats: churn={result['result']['data']['churn_rate']}%")


def test_database_premium_clients():
    init_database()
    result = get_premium_clients()
    assert result["row_count"] > 0
    assert all(r["tier"] == "Premium" for r in result["result"])
    print(f"\n✅ DB: {result['row_count']} clients Premium")


def test_database_open_tickets():
    result = get_open_tickets()
    assert "result" in result
    print(f"\n✅ DB tickets ouverts: {result['row_count']}")


def test_crm_lookup_by_id():
    result = crm_lookup(client_id="C001")
    assert result["result"]["company"] == "TechCorp SA"
    print(f"\n✅ CRM lookup: {result['result']['company']}")


def test_crm_at_risk():
    result = get_at_risk_clients()
    assert "result" in result
    print(f"\n✅ CRM at-risk: {result['count']} clients")


def test_pdf_generation():
    result = generate_pdf_report(
        title="Test Rapport",
        sections=[
            {"heading": "Section 1", "content": "Contenu test."},
            {"heading": "Clients", "content": [
                {"nom": "TechCorp", "tier": "Premium", "ca": 75000}
            ]},
        ],
        filename="test_report.pdf",
    )
    assert result["status"] == "success"
    assert os.path.exists(result["filepath"])
    print(f"\n✅ PDF généré: {result['filepath']} ({result['file_size_bytes']} bytes)")


if __name__ == "__main__":
    test_api_tool()
    test_api_stats()
    test_database_premium_clients()
    test_database_open_tickets()
    test_crm_lookup_by_id()
    test_crm_at_risk()
    test_pdf_generation()