"""
Coverage matrix for the RLM retrieval loop.
Defines which section types and node sections are required for each query intent.
The loop halts when all required coverage buckets are filled, or budget runs out.
"""

# Intent -> required coverage buckets
# Each bucket is (section_type, min_nodes) meaning we need at least min_nodes
# from that section type loaded before coverage is satisfied.
INTENT_COVERAGE = {
    "orient": [
        ("episodes", 2),
        ("patterns", 1),
        ("evolution", 1),
    ],
    "evolve": [
        ("causal", 3),
        ("evolution", 2),
        ("patterns", 1),
    ],
    "reflect": [
        ("episodes", 3),
        ("causal", 2),
        ("patterns", 1),
    ],
    "work": [
        ("procedures", 2),
        ("patterns", 1),
        ("episodes", 1),
    ],
    "general": [
        ("episodes", 1),
        ("patterns", 1),
        ("causal", 1),
    ],
    "causal_query": [
        ("causal", 5),
    ],
    "pattern_query": [
        ("patterns", 3),
        ("episodes", 2),
    ],
    "procedure_query": [
        ("procedures", 3),
    ],
}

# Default token budget for an RLM traversal (rough chars * tokens estimate)
DEFAULT_TOKEN_BUDGET = 4000

# Max hops before stopping even if coverage not met
MAX_HOPS = 10

# Semantic saturation: if last N hops produced no new section types, stop
SATURATION_WINDOW = 3


def get_required_coverage(intent: str) -> list:
    """Return list of (section_type, min_nodes) for the given intent."""
    return INTENT_COVERAGE.get(intent, INTENT_COVERAGE["general"])


def check_coverage(loaded_by_section: dict, required: list) -> tuple[bool, list]:
    """
    Check if coverage is satisfied.
    loaded_by_section: {section_type: [node_ids loaded so far]}
    required: [(section_type, min_nodes), ...]
    Returns (satisfied: bool, missing: [(section_type, still_needed), ...])
    """
    missing = []
    for sec_type, min_nodes in required:
        loaded_count = len(loaded_by_section.get(sec_type, []))
        if loaded_count < min_nodes:
            missing.append((sec_type, min_nodes - loaded_count))
    return len(missing) == 0, missing
