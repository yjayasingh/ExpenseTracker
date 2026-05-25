"""Tests for Flask API routes."""

from io import BytesIO

import database as db


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Expense Tracker" in response.data


def test_list_expenses_empty(client):
    response = client.get("/api/expenses")
    assert response.status_code == 200
    assert response.get_json() == []


def test_create_expense(client):
    response = client.post(
        "/api/expenses",
        data={
            "amount": "1500",
            "description": "Groceries",
            "category": "Food",
            "expense_date": "2026-05-25",
        },
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["amount"] == 1500.0
    assert data["description"] == "Groceries"
    assert data["category"] == "Food"


def test_create_expense_invalid_amount(client):
    response = client.post(
        "/api/expenses",
        data={"amount": "-5", "description": "X", "category": "Food"},
    )
    assert response.status_code == 400
    assert "Invalid amount" in response.get_json()["error"]


def test_create_expense_missing_description(client):
    response = client.post(
        "/api/expenses",
        data={"amount": "100", "description": "  ", "category": "Food"},
    )
    assert response.status_code == 400
    assert "Description" in response.get_json()["error"]


def test_create_expense_invalid_category(client):
    response = client.post(
        "/api/expenses",
        data={"amount": "100", "description": "X", "category": "Invalid"},
    )
    assert response.status_code == 400
    assert "Invalid category" in response.get_json()["error"]


def test_create_expense_with_receipt(client, temp_uploads):
    data = {
        "amount": "200",
        "description": "Dinner",
        "category": "Food",
        "expense_date": "2026-05-25",
        "receipt": (BytesIO(b"\x89PNG"), "bill.png"),
    }
    response = client.post("/api/expenses", data=data)
    assert response.status_code == 201
    body = response.get_json()
    assert body["receipt_path"] is not None
    assert body["receipt_url"].startswith("/uploads/receipts/")


def test_create_expense_invalid_receipt(client):
    data = {
        "amount": "100",
        "description": "X",
        "category": "Food",
        "receipt": (BytesIO(b"txt"), "file.txt"),
    }
    response = client.post("/api/expenses", data=data)
    assert response.status_code == 400


def test_delete_expense(client):
    eid = db.add_expense(50, "Temp", "Other", "2026-05-25")
    response = client.delete(f"/api/expenses/{eid}")
    assert response.status_code == 200
    assert db.get_expense(eid) is None


def test_delete_expense_not_found(client):
    response = client.delete("/api/expenses/99999")
    assert response.status_code == 404


def test_summary(client):
    db.add_expense(100, "A", "Food", "2026-05-10")
    response = client.get("/api/summary?month=2026-05")
    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] == 100
    assert data["count"] == 1


def test_categories(client):
    response = client.get("/api/categories")
    assert response.status_code == 200
    assert "Food" in response.get_json()


def test_export_expenses(client):
    db.add_expense(75, "Export me", "Shopping", "2026-05-25")
    response = client.get("/api/expenses/export")
    assert response.status_code == 200
    assert (
        response.mimetype
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment" in response.headers.get("Content-Disposition", "")
    assert len(response.data) > 0


def test_list_expenses_with_filters(client):
    db.add_expense(10, "May food", "Food", "2026-05-01")
    db.add_expense(20, "Jun food", "Food", "2026-06-01")

    response = client.get("/api/expenses?month=2026-05&category=Food")
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["description"] == "May food"
