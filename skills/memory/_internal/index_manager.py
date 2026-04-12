"""
Manages per-section _index.md card catalogs.
Each section has an index file listing all nodes for fast lookup without
traversing every file.
"""

import os
import datetime
from typing import Optional
from .md_parser import parse_frontmatter
from .md_writer import build_frontmatter

SECTIONS = ["episodes", "patterns", "procedures", "causal", "evolution"]


def _index_path(boros_dir: str, section: str) -> str:
    return os.path.join(boros_dir, "memory", "_indexes", f"{section}.md")


def _section_dir(boros_dir: str, section: str) -> str:
    return os.path.join(boros_dir, "memory", "sections", section)


def ensure_dirs(boros_dir: str):
    """Create all required memory directories."""
    os.makedirs(os.path.join(boros_dir, "memory", "_indexes"), exist_ok=True)
    for sec in SECTIONS:
        os.makedirs(os.path.join(boros_dir, "memory", "sections", sec), exist_ok=True)
    # Keep legacy dir alive for migration
    os.makedirs(os.path.join(boros_dir, "memory", "experiences"), exist_ok=True)


def read_index(boros_dir: str, section: str) -> list:
    """
    Read the section index. Returns list of entry dicts:
    [{"id": ..., "title": ..., "path": ..., "created": ...}, ...]
    """
    path = _index_path(boros_dir, section)
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    entries = []
    # Parse entries from the ## Index section
    in_index = False
    for line in content.splitlines():
        if line.strip() == "## Index":
            in_index = True
            continue
        if in_index and line.startswith("- "):
            # Format: - [id](rel_path) — title (date)
            try:
                bracket_end = line.index("]")
                entry_id = line[3:bracket_end]
                paren_end = line.index(")", bracket_end)
                rel_path = line[bracket_end + 2:paren_end]
                rest = line[paren_end + 1:].strip(" —").strip()
                entries.append({
                    "id": entry_id,
                    "path": os.path.join(boros_dir, "memory", "_indexes", rel_path),
                    "title": rest,
                })
            except (ValueError, IndexError):
                continue

    return entries


def add_to_index(boros_dir: str, section: str, entry_id: str,
                 title: str, rel_path: str):
    """Append a new entry to the section index. Creates index if missing."""
    idx_path = _index_path(boros_dir, section)

    # Load existing
    if os.path.exists(idx_path):
        with open(idx_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        fm = build_frontmatter({
            "section": section,
            "last_updated": datetime.datetime.utcnow().isoformat() + "Z",
            "count": 0,
        })
        content = fm + "\n\n## Index\n"

    # Update count in frontmatter
    meta, body = parse_frontmatter(content)
    meta["count"] = meta.get("count", 0) + 1
    meta["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"

    new_line = f"- [{entry_id}]({rel_path}) — {title}"
    if "## Index" in body:
        body = body.rstrip() + "\n" + new_line + "\n"
    else:
        body = body.rstrip() + "\n\n## Index\n" + new_line + "\n"

    new_content = build_frontmatter(meta) + "\n\n" + body.lstrip("\n")
    with open(idx_path, "w", encoding="utf-8") as f:
        f.write(new_content)


def get_node_path(boros_dir: str, section: str, entry_id: str) -> str:
    """Return absolute path for a memory node file."""
    return os.path.join(_section_dir(boros_dir, section), f"{entry_id}.md")


def section_for_type(entry_type: str) -> str:
    """Map entry type to section directory name."""
    mapping = {
        "episode": "episodes",
        "observation": "episodes",   # legacy compat
        "lesson": "episodes",        # legacy compat
        "pattern": "patterns",
        "procedure": "procedures",
        "causal": "causal",
        "fact": "causal",            # legacy compat
        "evolution": "evolution",
    }
    return mapping.get(entry_type, "episodes")
