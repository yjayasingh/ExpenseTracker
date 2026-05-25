"""Receipt image upload helpers."""

import uuid
from pathlib import Path

from werkzeug.utils import secure_filename

UPLOAD_DIR = Path(__file__).parent / "uploads" / "receipts"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def ensure_upload_dir():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def save_receipt(file_storage):
    """Save uploaded image; returns filename stored in DB."""
    if not file_storage or not file_storage.filename:
        return None

    original = secure_filename(file_storage.filename)
    if not original or not allowed_file(original):
        raise ValueError("Invalid image. Use PNG, JPG, GIF, or WebP.")

    file_storage.seek(0, 2)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > MAX_FILE_SIZE:
        raise ValueError("Image must be 5 MB or smaller.")

    ext = Path(original).suffix.lower()
    filename = f"{uuid.uuid4().hex}{ext}"

    ensure_upload_dir()
    file_storage.save(UPLOAD_DIR / filename)
    return filename


def delete_receipt(filename):
    if not filename:
        return
    path = UPLOAD_DIR / filename
    if path.is_file():
        path.unlink()


def receipt_url(filename):
    if not filename:
        return None
    return f"/uploads/receipts/{filename}"
