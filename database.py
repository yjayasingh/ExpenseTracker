"""SQLite persistence for expenses."""

import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).parent / "expenses.db"

CATEGORIES = [
    "Food",
    "Transport",
    "Housing",
    "Utilities",
    "Entertainment",
    "Healthcare",
    "Shopping",
    "Other",
]

MONTH_NAMES = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                expense_date TEXT NOT NULL,
                receipt_path TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        _migrate_receipt_column(conn)
        conn.commit()


def _migrate_receipt_column(conn):
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(expenses)").fetchall()
    }
    if "receipt_path" not in columns:
        conn.execute("ALTER TABLE expenses ADD COLUMN receipt_path TEXT")


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(row):
    from receipts import receipt_url

    receipt_path = row["receipt_path"] if "receipt_path" in row.keys() else None
    return {
        "id": row["id"],
        "amount": row["amount"],
        "description": row["description"],
        "category": row["category"],
        "expense_date": row["expense_date"],
        "receipt_path": receipt_path,
        "receipt_url": receipt_url(receipt_path),
        "created_at": row["created_at"],
    }


def add_expense(amount, description, category, expense_date, receipt_path=None):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO expenses (amount, description, category, expense_date, receipt_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (amount, description, category, expense_date, receipt_path),
        )
        conn.commit()
        return cursor.lastrowid


def get_expenses(month=None, category=None):
    query = "SELECT * FROM expenses WHERE 1=1"
    params = []

    if month:
        query += " AND expense_date LIKE ?"
        params.append(f"{month}%")

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY expense_date DESC, id DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [row_to_dict(r) for r in rows]


def get_available_years():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT substr(expense_date, 1, 4) AS year
            FROM expenses
            ORDER BY year DESC
            """
        ).fetchall()
    years = [row["year"] for row in rows if row["year"]]
    current_year = date.today().strftime("%Y")
    return years or [current_year]


def get_dashboard_data(year=None, month=None, category=None):
    year = year or date.today().strftime("%Y")
    category = category or None
    month = month or None

    query = "SELECT * FROM expenses WHERE expense_date LIKE ?"
    params = [f"{year}%"]

    if month:
        query += " AND expense_date LIKE ?"
        params.append(f"{year}-{int(month):02d}%")

    if category:
        query += " AND category = ?"
        params.append(category)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    expenses = [row_to_dict(row) for row in rows]
    total = round(sum(expense["amount"] for expense in expenses), 2)

    if month:
        chart = _daily_dashboard_chart(expenses)
    else:
        chart = _monthly_dashboard_chart(expenses)

    return {
        "total": total,
        "count": len(expenses),
        "year": year,
        "month": month or "",
        "category": category or "",
        "chart": chart,
    }


def _monthly_dashboard_chart(expenses):
    totals = {f"{month:02d}": 0 for month in range(1, 13)}
    for expense in expenses:
        expense_month = expense["expense_date"][5:7]
        totals[expense_month] = totals.get(expense_month, 0) + expense["amount"]

    return [
        {"label": MONTH_NAMES[index], "total": round(totals[f"{index + 1:02d}"], 2)}
        for index in range(12)
    ]


def _daily_dashboard_chart(expenses):
    totals = {}
    for expense in expenses:
        day = expense["expense_date"][8:10]
        totals[day] = totals.get(day, 0) + expense["amount"]

    return [
        {"label": str(int(day)), "total": round(totals[day], 2)}
        for day in sorted(totals)
    ]


def get_expense(expense_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
        return row_to_dict(row) if row else None


def delete_expense(expense_id):
    receipt_path = None
    with get_connection() as conn:
        row = conn.execute(
            "SELECT receipt_path FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
        if row:
            receipt_path = row["receipt_path"]
        cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
    return deleted, receipt_path


def get_summary(month=None):
    expenses = get_expenses(month=month)

    total = sum(e["amount"] for e in expenses)
    by_category = {}
    for e in expenses:
        by_category[e["category"]] = by_category.get(e["category"], 0) + e["amount"]

    category_breakdown = [
        {"category": cat, "total": by_category[cat]}
        for cat in sorted(by_category, key=lambda c: by_category[c], reverse=True)
    ]

    return {
        "total": round(total, 2),
        "count": len(expenses),
        "by_category": category_breakdown,
        "month": month or date.today().strftime("%Y-%m"),
    }
