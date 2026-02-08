"""
Quick API test using FastAPI TestClient (no server needed).
Run after: python migrate.py upgrade
"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}
    print("GET /health -> 200 OK")


def test_invoices_crud():
    # List with pagination (empty or existing)
    r = client.get("/invoices")
    assert r.status_code == 200
    data = r.json()
    assert "invoices" in data
    assert "pagination" in data
    p = data["pagination"]
    assert "total" in p and "page" in p and "page_size" in p and "total_pages" in p
    print("GET /invoices -> 200 OK", data)

    # Create
    payload = {
        "invoice_no": "INV-001",
        "issue_date": "2025-02-01",
        "due_date": "2025-02-28",
        "client_id": 1,
        "address": "123 Main St",
        "items": [{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 1}],
        "tax": 5.0,
    }
    r = client.post("/invoices", json=payload)
    assert r.status_code == 201
    inv = r.json()
    assert inv["invoice_no"] == "INV-001"
    assert inv["total"] > 0
    assert len(inv["items"]) == 2
    invoice_id = inv["id"]
    print("POST /invoices -> 201 OK", "id=", invoice_id)

    # Get by ID
    r = client.get(f"/invoices/{invoice_id}")
    assert r.status_code == 200
    assert r.json()["id"] == invoice_id
    print("GET /invoices/{id} -> 200 OK")

    # List again (with pagination)
    r = client.get("/invoices?page=1&page_size=10")
    assert r.status_code == 200
    data = r.json()
    assert any(i["id"] == invoice_id for i in data["invoices"])
    assert data["pagination"]["total"] >= 1 and data["pagination"]["page"] == 1
    print("GET /invoices (after create, paginated) -> 200 OK")

    # Delete
    r = client.delete(f"/invoices/{invoice_id}")
    assert r.status_code == 204
    print("DELETE /invoices/{id} -> 204 OK")

    # Get after delete -> 404
    r = client.get(f"/invoices/{invoice_id}")
    assert r.status_code == 404
    print("GET /invoices/{id} after delete -> 404 OK")


if __name__ == "__main__":
    test_health()
    test_invoices_crud()
    print("\nAll API tests passed.")
