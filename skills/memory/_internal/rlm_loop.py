"""
RLM (Retrieval Loop Memory) — iterative graph traversal engine.

Starting from seed nodes, follows forward links and backlinks until:
  1. Coverage satisfaction: required section buckets are filled
  2. Semantic saturation: no new section types seen in last SATURATION_WINDOW hops
  3. Token budget exhausted

Returns an ordered list of loaded node dicts, ready for synthesis.
"""

import os
from collections import deque
from typing import Optional

from .md_parser import parse_memory_md, extract_links, extract_backlinks
from .index_manager import SECTIONS, get_node_path, section_for_type, read_index
from .coverage import (
    get_required_coverage, check_coverage,
    DEFAULT_TOKEN_BUDGET, MAX_HOPS, SATURATION_WINDOW
)


def _load_node(boros_dir: str, node_id: str) -> Optional[dict]:
    """Load a node by ID. Returns parsed node dict or None."""
    for sec in SECTIONS:
        path = get_node_path(boros_dir, sec, node_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            parsed = parse_memory_md(content)
            parsed["_id"] = node_id
            parsed["_section"] = sec
            parsed["_path"] = path
            parsed["_char_count"] = len(content)
            return parsed
    return None


def _get_seeds_for_query(boros_dir: str, query: str, intent: str,
                          tags: list = None, limit: int = 5) -> list:
    """
    Find initial seed node IDs by scanning indexes for keyword matches.
    Prioritizes sections relevant to the intent.
    """
    from .coverage import get_required_coverage
    required = get_required_coverage(intent)
    # Ordered sections: required ones first
    priority_sections = [sec for sec, _ in required]
    all_sections = priority_sections + [s for s in SECTIONS if s not in priority_sections]

    seeds = []
    seen = set()
    query_lower = query.lower()
    tag_set = set(tags or [])

    for sec in all_sections:
        if len(seeds) >= limit:
            break
        entries = read_index(boros_dir, sec)
        for entry in reversed(entries):  # Most recent first
            if entry["id"] in seen:
                continue
            title_lower = entry.get("title", "").lower()
            if query_lower in title_lower:
                seeds.append(entry["id"])
                seen.add(entry["id"])
                if len(seeds) >= limit:
                    break

    # If not enough from title match, add most recent from priority sections
    if len(seeds) < 3:
        for sec in priority_sections:
            entries = read_index(boros_dir, sec)
            for entry in reversed(entries[-5:]):
                if entry["id"] not in seen and len(seeds) < limit:
                    seeds.append(entry["id"])
                    seen.add(entry["id"])

    return seeds


def run_rlm(boros_dir: str, query: str, intent: str = "general",
            tags: list = None, token_budget: int = None,
            seed_ids: list = None) -> list:
    """
    Run the RLM traversal.

    Returns list of loaded node dicts in traversal order, deduplicated.
    Each node dict: {"meta": {...}, "sections": {...}, "_id": ..., "_section": ..., "_char_count": ...}
    """
    budget = token_budget or DEFAULT_TOKEN_BUDGET
    # Rough: 1 char ≈ 0.25 tokens; budget is in tokens
    char_budget = budget * 4

    required = get_required_coverage(intent)

    # Find seeds
    if seed_ids:
        queue = deque(seed_ids)
    else:
        queue = deque(_get_seeds_for_query(boros_dir, query, intent, tags))

    visited = set()
    loaded_nodes = []
    loaded_by_section: dict[str, list] = {s: [] for s in SECTIONS}
    chars_used = 0
    hop = 0
    section_types_per_hop = []

    while queue and hop < MAX_HOPS and chars_used < char_budget:
        node_id = queue.popleft()
        if node_id in visited:
            continue
        visited.add(node_id)

        node = _load_node(boros_dir, node_id)
        if node is None:
            continue

        sec = node["_section"]
        loaded_nodes.append(node)
        loaded_by_section[sec].append(node_id)
        chars_used += node["_char_count"]
        section_types_per_hop.append(sec)

        # Check coverage
        satisfied, _ = check_coverage(loaded_by_section, required)
        if satisfied:
            break

        # Semantic saturation check
        if len(section_types_per_hop) >= SATURATION_WINDOW:
            recent = section_types_per_hop[-SATURATION_WINDOW:]
            if len(set(recent)) == 1:  # All same section type, no diversity
                # Only stop if coverage wasn't making progress
                _, missing_before = check_coverage(
                    {s: v[:max(0, len(v)-SATURATION_WINDOW)] for s, v in loaded_by_section.items()},
                    required
                )
                _, missing_after = check_coverage(loaded_by_section, required)
                if len(missing_after) >= len(missing_before):
                    break  # Saturated with no coverage progress

        # Enqueue neighbors (forward links then backlinks)
        forward = extract_links(node["meta"])
        backward = extract_backlinks(node["meta"])

        # Prioritize: links from same or needed sections first
        _, missing = check_coverage(loaded_by_section, required)
        needed_sections = {sec for sec, _ in missing}

        def _priority(nid: str) -> int:
            # Lower = higher priority
            for s in SECTIONS:
                path = get_node_path(boros_dir, s, nid)
                if os.path.exists(path):
                    return 0 if s in needed_sections else 1
            return 2

        neighbors = [n for n in (forward + backward) if n not in visited]
        neighbors.sort(key=_priority)
        queue.extendleft(reversed(neighbors))  # Prepend high-priority
        hop += 1

    return loaded_nodes
