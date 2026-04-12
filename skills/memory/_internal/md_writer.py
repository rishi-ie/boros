"""
Builds Obsidian-style markdown files from structured memory data.
Frontmatter is YAML-like (simple key: value, lists as indented items).
"""

import datetime
from typing import Any


def _yaml_value(v: Any) -> str:
    if isinstance(v, list):
        if not v:
            return "[]"
        lines = [""]
        for item in v:
            lines.append(f"  - {item}")
        return "\n".join(lines)
    if isinstance(v, dict):
        if not v:
            return "{}"
        lines = [""]
        for k, dv in v.items():
            lines.append(f"  {k}: {dv}")
        return "\n".join(lines)
    if v is None:
        return "null"
    if isinstance(v, bool):
        return str(v).lower()
    return str(v)


def build_frontmatter(fields: dict) -> str:
    """Render a dict as YAML frontmatter block."""
    lines = ["---"]
    for k, v in fields.items():
        rendered = _yaml_value(v)
        if rendered.startswith("\n"):
            lines.append(f"{k}:{rendered}")
        else:
            lines.append(f"{k}: {rendered}")
    lines.append("---")
    return "\n".join(lines)


def build_memory_md(meta: dict, sections: dict) -> str:
    """
    Build a complete memory markdown document.

    meta   — frontmatter fields (id, type, title, created, tags, links, backlinked_by, ...)
    sections — ordered dict of section_name -> body_text
               e.g. {"Summary": "...", "Context": "...", "Action": "...", "Outcome": "..."}
    """
    front = build_frontmatter(meta)
    body_parts = [front, ""]
    for section_name, body in sections.items():
        body_parts.append(f"## {section_name}")
        body_parts.append(body.strip() if body else "")
        body_parts.append("")
    return "\n".join(body_parts).rstrip() + "\n"


def default_meta(entry_id: str, entry_type: str, title: str = "",
                 tags: list = None, links: list = None) -> dict:
    """Build default frontmatter fields for a new memory node."""
    return {
        "id": entry_id,
        "type": entry_type,
        "title": title or entry_id,
        "created": datetime.datetime.utcnow().isoformat() + "Z",
        "tags": tags or [],
        "links": links or [],
        "backlinked_by": [],
    }


def causal_meta(entry_id: str, subject: str, predicate: str, object_val: str,
                cycle: int = None, valid_from: str = None, valid_until=None,
                metadata: dict = None, tags: list = None) -> dict:
    """Build frontmatter fields for a causal (KG-style) memory node."""
    return {
        "id": entry_id,
        "type": "causal",
        "subject": subject,
        "predicate": predicate,
        "object": object_val,
        "cycle": cycle,
        "valid_from": valid_from or (datetime.datetime.utcnow().isoformat() + "Z"),
        "valid_until": valid_until,
        "tags": tags or [subject, predicate],
        "links": [],
        "backlinked_by": [],
        "metadata": metadata or {},
    }
