"""Shared pytest fixtures."""

import pytest

import database as db
import receipts


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    """Use an isolated SQLite database per test."""
    db_path = tmp_path / "test_expenses.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    db.init_db()
    yield db_path


@pytest.fixture
def temp_uploads(monkeypatch, tmp_path):
    """Use an isolated upload directory per test."""
    upload_dir = tmp_path / "receipts"
    monkeypatch.setattr(receipts, "UPLOAD_DIR", upload_dir)
    yield upload_dir


@pytest.fixture
def client(temp_db, temp_uploads):
    """Flask test client with isolated DB and uploads."""
    from app import app

    app.config["TESTING"] = True
    app._db_initialized = False

    with app.test_client() as test_client:
        yield test_client

    app._db_initialized = False
