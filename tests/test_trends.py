"""Tests for monthly expense trends."""

import database as db


def test_monthly_trends_empty(temp_db):
    result = db.get_monthly_trends()
    assert result["years"] == []
    assert result["trends"] == {}


def test_monthly_trends_single_year(temp_db):
    db.add_expense(100, "A", "Food", "2026-01-15")
    db.add_expense(200, "B", "Food", "2026-03-10")
    db.add_expense(50, "C", "Food", "2026-03-20")

    result = db.get_monthly_trends()

    assert result["years"] == [2026]
    trend = result["trends"]["2026"]
    assert trend["year"] == 2026
    assert trend["labels"] == db.MONTH_LABELS
    assert trend["totals"][0] == 100  # Jan
    assert trend["totals"][2] == 250  # Mar
    assert trend["year_total"] == 350


def test_monthly_trends_multiple_years(temp_db):
    db.add_expense(500, "Old", "Food", "2025-06-01")
    db.add_expense(300, "New", "Food", "2026-02-01")

    result = db.get_monthly_trends()

    assert result["years"] == [2026, 2025]
    assert result["trends"]["2025"]["totals"][5] == 500
    assert result["trends"]["2026"]["totals"][1] == 300


def test_monthly_trends_filter_by_category(temp_db):
    db.add_expense(100, "Lunch", "Food", "2026-01-10")
    db.add_expense(400, "Bus", "Transport", "2026-01-15")
    db.add_expense(50, "Snack", "Food", "2026-02-01")

    result = db.get_monthly_trends(category="Food")

    assert result["category"] == "Food"
    assert result["trends"]["2026"]["totals"][0] == 100
    assert result["trends"]["2026"]["totals"][1] == 50
    assert result["trends"]["2026"]["year_total"] == 150


def test_api_trends(client, temp_db):
    db.add_expense(75, "Test", "Other", "2026-05-01")
    response = client.get("/api/trends")
    assert response.status_code == 200
    data = response.get_json()
    assert 2026 in data["years"]
    assert data["trends"]["2026"]["year_total"] == 75


def test_api_trends_category_filter(client, temp_db):
    db.add_expense(100, "A", "Food", "2026-05-01")
    db.add_expense(200, "B", "Transport", "2026-05-02")
    response = client.get("/api/trends?category=Food")
    assert response.status_code == 200
    data = response.get_json()
    assert data["category"] == "Food"
    assert data["trends"]["2026"]["year_total"] == 100


def test_api_trends_invalid_category(client):
    response = client.get("/api/trends?category=Invalid")
    assert response.status_code == 400
