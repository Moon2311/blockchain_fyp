"""Upload directory, Fernet key, and file helpers (shared by API routes)."""

from __future__ import annotations

import hashlib
import os

from cryptography.fernet import Fernet

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
UPLOAD_DIR = os.path.join(ROOT_DIR, "uploads")
KEY_FILE = os.path.join(BASE_DIR, "fernet.key")

os.makedirs(UPLOAD_DIR, exist_ok=True)

if os.path.exists(KEY_FILE):
    with open(KEY_FILE, "rb") as f:
        FERNET_KEY = f.read()
else:
    FERNET_KEY = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(FERNET_KEY)

fernet = Fernet(FERNET_KEY)

ALLOWED_EXTENSIONS = {
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "mp3",
    "wav",
    "mp4",
    "avi",
    "gif",
    "txt",
    "log",
    "docx",
    "xlsx",
    "csv",
    "zip",
    "pcap",
    "json",
}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
