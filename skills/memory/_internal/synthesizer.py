"""
Assembles a structured DRG (Directed Retrieval Generation) brief from
a list of loaded RLM nodes.

The brief is a dict with section-keyed summaries for direct LLM consumption.
It also produces a flat `results` list for backward-compatible callers.
"""

from .index_manager import SECTIONS


def _node_summary(node: dict) -> dict:
    """Extract key fields from a parsed node for the brief."""
    meta = node.get("meta", {})
    sections = node.get("sections", {})
    return {
        "id": node.get("_id", meta.get("id", "unknown")),
        "type": meta.get("type", "unknown"),
        "section": node.get("_section", "unknown"),
        "title": meta.get("title", ""),
        "created": meta.get("created", ""),
        "tags": meta.get("tags", []),
        "summary": sections.get("Summary", ""),
        "context": sections.get("Context", ""),
        "action": sections.get("Action", ""),
        "outcome": sections.get("Outcome", ""),
        "notes": sections.get("Notes", ""),
        # Causal fields
        "subject": meta.get("subject"),
        "predicate": meta.get("predicate"),
        "object": meta.get("object"),
        "cycle": meta.get("cycle"),
        "metadata": meta.get("metadata"),
        "links": meta.get("links", []),
        "backlinked_by": meta.get("backlinked_by", []),
    }


def synthesize_brief(nodes: list, query: str = "", intent: str = "general") -> dict:
    """
    Build a structured DRG brief from RLM-loaded nodes.

    Returns:
    {
        "query": ...,
        "intent": ...,
        "node_count": N,
        "by_section": {
            "episodes": [...],
            "patterns": [...],
            "procedures": [...],
            "causal": [...],
            "evolution": [...],
        },
        "results": [...],   # flat list — backward compat for evolve_orient.py
        "narrative": "..."  # prose summary for LLM context injection
    }
    """
    by_section: dict[str, list] = {s: [] for s in SECTIONS}
    flat_results = []

    for node in nodes:
        summary = _node_summary(node)
        sec = node.get("_section", "episodes")
        by_section.setdefault(sec, []).append(summary)
        # Backward-compatible flat result (matches old memory_search_sql output)
        flat_result = {
            "id": summary["id"],
            "entry_type": summary["type"],
            "content": _node_to_content(summary),
            "tags": summary["tags"],
            "timestamp": summary["created"],
        }
        flat_results.append(flat_result)

    narrative = _build_narrative(by_section, query, intent)

    return {
        "query": query,
        "intent": intent,
        "node_count": len(nodes),
        "by_section": by_section,
        "results": flat_results,
        "narrative": narrative,
    }


def _node_to_content(summary: dict) -> str:
    """Reconstruct a text content string for backward-compat flat results."""
    if summary.get("subject"):
        return (f"Context: {summary['subject']} {summary['predicate']} {summary['object']} "
                f"(cycle {summary['cycle']})")
    parts = []
    if summary["context"]:
        parts.append(f"Context: {summary['context']}")
    if summary["action"]:
        parts.append(f"Action: {summary['action']}")
    if summary["outcome"]:
        parts.append(f"Outcome: {summary['outcome']}")
    return " ".join(parts) or summary["summary"] or summary["title"]


def _build_narrative(by_section: dict, query: str, intent: str) -> str:
    """Build a compact prose narrative for LLM injection."""
    parts = []

    if by_section.get("causal"):
        causal_lines = []
        for n in by_section["causal"][:5]:
            if n.get("subject"):
                causal_lines.append(
                    f"  - {n['subject']} {n['predicate']} {n['object']}"
                    + (f" (cycle {n['cycle']})" if n.get("cycle") else "")
                )
        if causal_lines:
            parts.append("**Causal facts:**\n" + "\n".join(causal_lines))

    if by_section.get("episodes"):
        ep_lines = []
        for n in by_section["episodes"][:3]:
            line = f"  - [{n['id']}] {n['title'] or n['summary'][:80]}"
            if n.get("outcome"):
                line += f" → {n['outcome'][:60]}"
            ep_lines.append(line)
        if ep_lines:
            parts.append("**Episodes:**\n" + "\n".join(ep_lines))

    if by_section.get("patterns"):
        pat_lines = [f"  - {n['title'] or n['summary'][:80]}"
                     for n in by_section["patterns"][:3]]
        if pat_lines:
            parts.append("**Patterns:**\n" + "\n".join(pat_lines))

    if by_section.get("procedures"):
        proc_lines = [f"  - {n['title'] or n['summary'][:80]}"
                      for n in by_section["procedures"][:3]]
        if proc_lines:
            parts.append("**Procedures:**\n" + "\n".join(proc_lines))

    if by_section.get("evolution"):
        evo_lines = [f"  - {n['title'] or n['summary'][:80]}"
                     for n in by_section["evolution"][:3]]
        if evo_lines:
            parts.append("**Evolution history:**\n" + "\n".join(evo_lines))

    return "\n\n".join(parts)
