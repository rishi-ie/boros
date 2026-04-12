"""
SHIM — delegates to memory_store.
Kept for backward compatibility. Do not remove until all callers are updated.
"""

from .memory_store import memory_store


def memory_commit_archival(params: dict, kernel=None) -> dict:
    """Commit an entry to long-term archival memory. Shim → memory_store."""
    entry_type = params.get("entry_type", "episode")
    store_params = {
        "type":    entry_type,
        "content": params.get("content", ""),
        "tags":    params.get("tags", []),
        "title":   params.get("title", ""),
    }
    result = memory_store(store_params, kernel)
    if result.get("status") == "ok":
        return {
            "status": "ok",
            "entry_id": result["entry_id"],
            "entry_type": entry_type,
            "timestamp": result["timestamp"],
        }
    return result
