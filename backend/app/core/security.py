"""Security helpers (hashing, challenge ID generation)."""
from __future__ import annotations
import hashlib
import hmac
import json
import uuid


def generate_id(prefix: str = "") -> str:
    """Generate a URL-safe unique ID."""
    uid = uuid.uuid4().hex
    return f"{prefix}{uid}" if prefix else uid


def hash_scores(scores: dict) -> str:
    """SHA-256 hex digest of scores dict (deterministic JSON)."""
    payload = json.dumps(scores, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
