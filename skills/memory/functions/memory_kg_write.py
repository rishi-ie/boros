"""
SHIM — delegates to memory_store(type="causal").
Kept for backward compatibility (loop_end_cycle.py uses kernel.registry["memory_kg_write"]).
Do not remove until all callers are updated to use memory_store directly.
"""

from .memory_store import memory_store


def memory_kg_write(params: dict, kernel=None) -> dict:
    """Record a temporal fact about a skill or category. Shim → memory_store(type='causal')."""
    store_params = {
        "type": "causal",
        "subject":    params.get("subject", ""),
        "predicate":  params.get("predicate", ""),
        "object":     params.get("object", ""),
        "cycle":      params.get("cycle"),
        "valid_from": params.get("valid_from"),
        "metadata":   params.get("metadata", {}),
        "tags":       [params.get("subject", ""), params.get("predicate", "")],
    }
    result = memory_store(store_params, kernel)
    if result.get("status") == "ok":
        # Return shape old callers expect
        return {
            "status": "ok",
            "triple_id": result["entry_id"],
            "subject": params.get("subject"),
            "predicate": params.get("predicate"),
            "object": params.get("object"),
        }
    return result
