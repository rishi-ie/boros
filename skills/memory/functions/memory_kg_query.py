"""
SHIM — delegates to memory_retrieve with subject-based causal query.
Kept for backward compatibility (evolve_orient.py uses kernel.registry["memory_kg_query"]).
Do not remove until all callers are updated to use memory_retrieve directly.
"""

from .memory_retrieve import memory_retrieve


def memory_kg_query(params: dict, kernel=None) -> dict:
    """Query facts about a skill or category. Shim → memory_retrieve(subject=...)."""
    result = memory_retrieve(params, kernel)
    if result.get("status") != "ok":
        return result

    # Old callers expect: {status, subject, facts, count}
    # evolve_orient.py specifically checks result.get("results", [])
    # so we need to keep "results" key (already in memory_retrieve response)
    # but also add "facts" shape for any code that uses the old KG return
    flat_results = result.get("results", [])

    # Convert flat results → facts shape
    facts = []
    for r in flat_results:
        facts.append({
            "id":         r.get("id"),
            "predicate":  r.get("predicate", ""),
            "object":     r.get("object", ""),
            "valid_from": r.get("timestamp", ""),
            "valid_until": None,
            "cycle":      r.get("cycle"),
            "metadata":   r.get("metadata"),
        })

    return {
        "status": "ok",
        "subject": params.get("subject", ""),
        "facts": facts,
        "count": len(facts),
        "results": flat_results,   # evolve_orient.py reads this key
    }
