"""
memory_retrieve — unified read function for the RLM memory system.

Replaces: memory_search_sql + memory_kg_query

Uses the RLM (Retrieval Loop Memory) traversal to find relevant nodes
and returns a DRG (Directed Retrieval Generation) structured brief.

Return shape always includes:
  status     — "ok" or "error"
  results    — flat list (backward-compat with evolve_orient.py etc.)
  brief      — DRG structured brief (by_section, narrative)
  node_count — number of nodes loaded
"""

import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_skill_root = os.path.dirname(_here)
if _skill_root not in sys.path:
    sys.path.insert(0, _skill_root)

from _internal.rlm_loop import run_rlm
from _internal.synthesizer import synthesize_brief
from _internal.index_manager import ensure_dirs, SECTIONS, get_node_path
from _internal.md_parser import parse_memory_md


def _search_by_subject_predicate(boros_dir: str, subject: str,
                                  predicate: str = None,
                                  include_history: bool = False,
                                  as_of: str = None) -> list:
    """
    Backward-compat: find causal nodes matching subject (+ optional predicate).
    Scans causal section directory.
    """
    causal_dir = os.path.join(boros_dir, "memory", "sections", "causal")
    if not os.path.exists(causal_dir):
        return []

    results = []
    for fname in os.listdir(causal_dir):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(causal_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue

        parsed = parse_memory_md(content)
        meta = parsed["meta"]

        if meta.get("subject") != subject:
            continue
        if predicate and meta.get("predicate") != predicate:
            continue

        # Temporal filter
        valid_until = meta.get("valid_until")
        if not include_history and valid_until is not None:
            continue  # This fact has been superseded

        if as_of:
            valid_from = meta.get("valid_from", "")
            if valid_from > as_of:
                continue  # Not yet valid at that point in time

        results.append({
            "id": meta.get("id", fname[:-3]),
            "entry_type": "causal",
            "content": (f"Context: {meta.get('subject')} {meta.get('predicate')} "
                       f"{meta.get('object')} (cycle {meta.get('cycle')})"),
            "tags": meta.get("tags", []),
            "timestamp": meta.get("valid_from", ""),
            "subject": meta.get("subject"),
            "predicate": meta.get("predicate"),
            "object": meta.get("object"),
            "cycle": meta.get("cycle"),
            "metadata": meta.get("metadata"),
        })

    return results


def memory_retrieve(params: dict, kernel=None) -> dict:
    """
    Retrieve relevant memories using RLM traversal.

    Params:
      query          (str)  — what you're looking for
      intent         (str)  — orient / evolve / reflect / work / general / causal_query
                              Determines coverage requirements
      tags           (list) — optional tag filter
      seed_ids       (list) — start traversal from specific node IDs
      token_budget   (int)  — max tokens to load (default 4000)

    Backward-compat params (maps to causal_query):
      subject        (str)  — for KG-style subject lookup
      predicate      (str)  — filter by predicate
      include_history (bool) — include superseded facts
      as_of          (str)  — point-in-time query (ISO timestamp)

    Returns:
      {status, results, brief, node_count, narrative}
    """
    boros_dir = str(kernel.boros_root) if kernel else os.getcwd()
    ensure_dirs(boros_dir)

    # ── Backward-compat: KG-style subject query ──────────────────────────────
    subject = params.get("subject")
    if subject:
        predicate = params.get("predicate")
        include_history = params.get("include_history", False)
        as_of = params.get("as_of")
        results = _search_by_subject_predicate(
            boros_dir, subject, predicate, include_history, as_of
        )
        return {
            "status": "ok",
            "results": results,
            "node_count": len(results),
            "brief": {"query": subject, "intent": "causal_query", "by_section": {"causal": results}},
            "narrative": "\n".join(r["content"] for r in results[:10]),
        }

    # ── Standard RLM retrieval ────────────────────────────────────────────────
    query = params.get("query", "")
    if not query:
        return {"status": "error", "message": "query or subject required"}

    intent = params.get("intent", "general")
    tags = params.get("tags", [])
    seed_ids = params.get("seed_ids", [])
    token_budget = params.get("token_budget")

    # Also try legacy SQL-style query fallback on old .json files
    nodes = run_rlm(
        boros_dir, query, intent=intent, tags=tags,
        token_budget=token_budget, seed_ids=seed_ids or None
    )

    brief = synthesize_brief(nodes, query=query, intent=intent)

    return {
        "status": "ok",
        "results": brief["results"],
        "node_count": brief["node_count"],
        "brief": brief,
        "narrative": brief["narrative"],
    }
