"""Identity utilities for the Boros civilization skill."""

import hashlib
import json
import uuid
from pathlib import Path


def generate_instance_id() -> str:
    """Generate a short UUID-based instance ID."""
    return f"boros-{uuid.uuid4().hex[:8]}"


def compute_world_model_hash(boros_root: Path) -> str:
    """SHA-256 hash of the world model for divergence detection.

    Returns a truncated hash prefixed with 'sha256:'.
    If no world model exists, returns 'sha256:none'.
    """
    wm_path = boros_root / "world_model.json"
    if not wm_path.exists():
        return "sha256:none"
    try:
        content = wm_path.read_text(encoding="utf-8")
        h = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"sha256:{h}"
    except Exception:
        return "sha256:error"
