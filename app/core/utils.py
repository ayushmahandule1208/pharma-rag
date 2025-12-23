"""Utility functions."""
import hashlib
import re
from pathlib import Path


def file_hash(path: Path) -> str:
    """SHA-256 hash for file dedup."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_fingerprint(text: str) -> str:
    """Normalized MD5 for content dedup."""
    normalized = re.sub(r"\s+", " ", text.lower().strip())
    normalized = re.sub(r"[^\w\s]", "", normalized)
    return hashlib.md5(normalized.encode()).hexdigest()
