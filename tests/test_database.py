"""Tests for database module."""

import database as db


def test_init_db_creates_table(temp_db):
    with db.get_connection() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='expenses'"
        ).fetchone()
    assert tables is not None


def test_add_and_get_expense(temp_db):
    eid = db.add_expense(1500.5, "Lunch", "Food", "2026-05-20")
    expense = db.get_expense(eid)

    assert expense["id"] == eid
    assert expense["amount"] == 1500.5
    assert expense["description"] == "Lunch"
    assert expense["category"] == "Food"
    assert expense["expense_date"] == "2026-05-20"
    assert expense["receipt_path"] is None
    assert expense["receipt_url"] is None


def test_add_expense_with_receipt_path(temp_db):
    eid = db.add_expense(100, "Taxi", "Transport", "2026-05-21", "abc.png")
    expense = db.get_expense(eid)

    assert expense["receipt_path"] == "abc.png"
    assert expense["receipt_url"] == "/uploads/receipts/abc.png"


def test_get_expenses_filter_by_month(temp_db):
    db.add_expense(100, "A", "Food", "2026-05-01")
    db.add_expense(200, "B", "Food", "2026-06-01")

    may = db.get_expenses(month="2026-05")
    assert len(may) == 1
    assert may[0]["description"] == "A"


def test_get_expenses_filter_by_category(temp_db):
    db.add_expense(100, "A", "Food", "2026-05-01")
    db.add_expense(200, "B", "Transport", "2026-05-02")

    food = db.get_expenses(category="Food")
    assert len(food) == 1
    assert food[0]["category"] == "Food"


def test_get_expense_not_found(temp_db):
    assert db.get_expense(9999) is None


def test_delete_expense(temp_db):
    eid = db.add_expense(50, "Snack", "Food", "2026-05-10", "receipt.jpg")
    deleted, receipt_path = db.delete_expense(eid)

    assert deleted is True
    assert receipt_path == "receipt.jpg"
    assert db.get_expense(eid) is None


def test_delete_expense_not_found(temp_db):
    deleted, receipt_path = db.delete_expense(9999)
    assert deleted is False
    assert receipt_path is None


def test_get_summary(temp_db):
    db.add_expense(100, "A", "Food", "2026-05-01")
    db.add_expense(300, "B", "Transport", "2026-05-15")
    db.add_expense(50, "C", "Food", "2026-05-20")

    summary = db.get_summary(month="2026-05")

    assert summary["total"] == 450
    assert summary["count"] == 3
    assert summary["month"] == "2026-05"
    assert summary["by_category"] == [
        {"category": "Transport", "total": 300},
        {"category": "Food", "total": 150},
    ]


def test_get_summary_empty(temp_db):
    summary = db.get_summary(month="2026-01")
    assert summary["total"] == 0
    assert summary["count"] == 0
    assert summary["by_category"] == []
