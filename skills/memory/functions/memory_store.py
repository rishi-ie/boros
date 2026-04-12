"""
memory_store — unified write function for the RLM memory system.

Replaces: memory_commit_archival + memory_kg_write

Writes an Obsidian-style .md node to the appropriate section directory,
updates the section index, and maintains bidirectional backlinks.

type options:
  "episode"   — what happened (event/experience)
  "pattern"   — recurring behavior or observation
  "procedure" — how-to / step-by-step
  "causal"    — cause-effect (subject/predicate/object, replaces KG triples)
  "evolution" — evolution-specific records

For type="causal", accepts flat params: subject, predicate, object, cycle, metadata.
For other types, accepts: title, content (parsed for Context/Action/Outcome), sections dict.
"""

import os
import uuid
import datetime
import sys

# Allow relative imports when loaded as a standalone skill function
_here = os.path.dirname(os.path.abspath(__file__))
_skill_root = os.path.dirname(_here)
if _skill_root not in sys.path:
    sys.path.insert(0, _skill_root)

from _internal.md_writer import build_memory_md, default_meta, causal_meta
from _internal.index_manager import (
    ensure_dirs, section_for_type, get_node_path, add_to_index, SECTIONS
)
from _internal.backlink_manager import update_backlinks


def _parse_content_sections(content: str) -> dict:
    """
    Parse a freeform content string into sections dict.
    Looks for Context:, Action:, Outcome: markers (legacy compat).
    Falls back to putting everything in Summary.
    """
    sections = {}
    markers = ["Context:", "Action:", "Outcome:", "Notes:"]
    has_markers = any(m in content for m in markers)

    if not has_markers:
        sections["Summary"] = content.strip()
        return sections

    # Split on markers
    remaining = content
    order = []
    positions = {}
    for m in markers:
        idx = content.find(m)
        if idx != -1:
            positions[idx] = m
    for idx in sorted(positions):
        order.append(positions[idx])

    for i, marker in enumerate(order):
        start = content.find(marker) + len(marker)
        end = len(content)
        for j in range(i + 1, len(order)):
            next_idx = content.find(order[j])
            if next_idx != -1 and next_idx > start:
                end = next_idx
                break
        section_name = marker.rstrip(":")
        sections[section_name] = content[start:end].strip()

    return sections


def memory_store(params: dict, kernel=None) -> dict:
    """
    Store a memory node.

    Common params:
      type        (str)  — episode / pattern / procedure / causal / evolution
      title       (str)  — human-readable title
      content     (str)  — freeform text, or Context:/Action:/Outcome: structured
      tags        (list) — tag strings
      links       (list) — forward link IDs to other nodes
      sections    (dict) — explicit section dict (overrides content parsing)

    Causal-specific (type="causal"):
      subject     (str)  — entity (skill name, category)
      predicate   (str)  — relationship type (has_score, caused_delta_in, ...)
      object      (str)  — value or related entity
      cycle       (int)  — cycle number
      valid_from  (str)  — ISO timestamp
      metadata    (dict) — extra data

    Returns: {status, entry_id, type, section, timestamp}
    """
    boros_dir = str(kernel.boros_root) if kernel else os.getcwd()
    ensure_dirs(boros_dir)

    entry_type = params.get("type", params.get("entry_type", "episode"))
    section = section_for_type(entry_type)

    entry_id_prefix = {
        "causal": "caus",
        "episodes": "ep",
        "patterns": "pat",
        "procedures": "proc",
        "evolution": "evo",
    }.get(section, "mem")

    entry_id = f"{entry_id_prefix}-{uuid.uuid4().hex[:8]}"
    tags = params.get("tags", [])
    links = params.get("links", [])

    if entry_type in ("causal", "fact"):
        subject = params.get("subject", "")
        predicate = params.get("predicate", "")
        object_val = params.get("object", "")
        cycle = params.get("cycle")
        valid_from = params.get("valid_from")
        metadata = params.get("metadata", {})

        if not subject or not predicate or not object_val:
            return {"status": "error", "message": "causal type requires subject, predicate, object"}

        meta = causal_meta(
            entry_id, subject, predicate, object_val,
            cycle=cycle, valid_from=valid_from,
            metadata=metadata, tags=tags or [subject, predicate]
        )
        summary = f"{subject} {predicate} {object_val}"
        if cycle is not None:
            summary += f" (cycle {cycle})"
        sections_dict = {"Summary": summary}

    else:
        # Narrative types
        title = params.get("title", "")
        content = params.get("content", "")
        explicit_sections = params.get("sections")

        if not content and not explicit_sections and not title:
            return {"status": "error", "message": "content, sections, or title required"}

        # Validate lesson/observation content structure (legacy compat)
        if entry_type in ("lesson", "observation") and content:
            required_phrases = ["Context:", "Action:", "Outcome:"]
            if not all(p in content for p in required_phrases):
                return {
                    "status": "error",
                    "message": f"For type '{entry_type}', content must include: {required_phrases}"
                }
            if len(content.strip()) < 100:
                return {"status": "error", "message": "Content too short (min 100 chars)."}

        meta = default_meta(entry_id, entry_type, title=title, tags=tags, links=links)

        if explicit_sections:
            sections_dict = explicit_sections
        elif content:
            sections_dict = _parse_content_sections(content)
            if "Summary" not in sections_dict and title:
                sections_dict = {"Summary": title, **sections_dict}
        else:
            sections_dict = {"Summary": title}

    # Write .md file
    node_path = get_node_path(boros_dir, section, entry_id)
    os.makedirs(os.path.dirname(node_path), exist_ok=True)
    md_content = build_memory_md(meta, sections_dict)
    try:
        with open(node_path, "w", encoding="utf-8") as f:
            f.write(md_content)
    except OSError as e:
        return {"status": "error", "message": f"Failed to write memory file: {e}"}

    # Update index
    title_for_index = (
        meta.get("title") or
        f"{meta.get('subject', '')} {meta.get('predicate', '')}" or
        entry_id
    )
    rel_path = os.path.relpath(node_path,
                               os.path.join(boros_dir, "memory", "_indexes"))
    add_to_index(boros_dir, section, entry_id, title_for_index, rel_path)

    # Maintain bidirectional backlinks
    update_backlinks(boros_dir, entry_id, links, old_links=[])

    timestamp = meta.get("created", meta.get("valid_from", datetime.datetime.utcnow().isoformat() + "Z"))
    return {
        "status": "ok",
        "entry_id": entry_id,
        "type": entry_type,
        "section": section,
        "timestamp": timestamp,
    }
