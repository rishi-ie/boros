"""
SHIM — delegates to memory_retrieve.
Kept for backward compatibility. Do not remove until all callers are updated.
"""

from .memory_retrieve import memory_retrieve


def memory_search_sql(params: dict, kernel=None) -> dict:
    """Search memory files using a keyword query. Shim → memory_retrieve."""
    query = params.get("query", "")
    if not query:
        return {"status": "error", "message": "query required"}

    result = memory_retrieve({"query": query, "intent": "general"}, kernel)
    if result.get("status") != "ok":
        return result

    # Return old shape: {status, query, matches, total, method}
    matches = []
    for r in result.get("results", []):
        matches.append({
            "source": "rlm",
            "id": r.get("id"),
            "type": r.get("entry_type"),
            "preview": r.get("content", "")[:300],
            "tags": r.get("tags", []),
            "timestamp": r.get("timestamp", ""),
        })

    return {
        "status": "ok",
        "query": query,
        "matches": matches,
        "total": len(matches),
        "method": "rlm",
    }
