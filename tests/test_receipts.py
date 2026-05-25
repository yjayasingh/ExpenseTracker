"""Tests for receipts module."""

from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage

import receipts


def _file_storage(data: bytes, filename: str) -> FileStorage:
    return FileStorage(stream=BytesIO(data), filename=filename)


def test_allowed_file():
    assert receipts.allowed_file("photo.png") is True
    assert receipts.allowed_file("photo.JPG") is True
    assert receipts.allowed_file("doc.pdf") is False


def test_receipt_url():
    assert receipts.receipt_url(None) is None
    assert receipts.receipt_url("abc.png") == "/uploads/receipts/abc.png"


def test_save_receipt_png(temp_uploads):
    storage = _file_storage(b"\x89PNG fake", "receipt.png")
    filename = receipts.save_receipt(storage)

    assert filename.endswith(".png")
    assert (temp_uploads / filename).is_file()


def test_save_receipt_empty_returns_none(temp_uploads):
    assert receipts.save_receipt(None) is None
    assert receipts.save_receipt(_file_storage(b"x", "")) is None


def test_save_receipt_invalid_extension(temp_uploads):
    storage = _file_storage(b"data", "file.pdf")
    with pytest.raises(ValueError, match="Invalid image"):
        receipts.save_receipt(storage)


def test_save_receipt_too_large(temp_uploads):
    big = b"x" * (receipts.MAX_FILE_SIZE + 1)
    storage = _file_storage(big, "big.png")
    with pytest.raises(ValueError, match="5 MB"):
        receipts.save_receipt(storage)


def test_delete_receipt(temp_uploads):
    storage = _file_storage(b"img", "r.jpg")
    filename = receipts.save_receipt(storage)
    path = temp_uploads / filename

    receipts.delete_receipt(filename)
    assert not path.is_file()

    receipts.delete_receipt(None)
    receipts.delete_receipt("missing.png")
