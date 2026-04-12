"""
Parses Obsidian-style markdown memory files.
Returns structured dict with 'meta' and 'sections'.
"""

import re
from typing import Any


def _parse_yaml_value(raw: str) -> Any:
    """Parse a simple YAML scalar or inline list."""
    raw = raw.strip()
    if raw == "null":
        return None
    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw == "[]":
        return []
    if raw == "{}":
        return {}
    # Try integer
    try:
        return int(raw)
    except ValueError:
        pass
    # Try float
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """
    Split markdown text into (frontmatter_dict, body).
    Returns ({}, text) if no frontmatter found.
    """
    if not text.startswith("---"):
        return {}, text

    end_idx = text.find("\n---", 3)
    if end_idx == -1:
        return {}, text

    fm_block = text[3:end_idx].strip()
    body = text[end_idx + 4:].lstrip("\n")

    meta = {}
    current_key = None
    current_list = None

    for line in fm_block.splitlines():
        # List item continuation
        if line.startswith("  - ") and current_key is not None:
            if current_list is None:
                current_list = []
                meta[current_key] = current_list
            current_list.append(line[4:].strip())
            continue

        # Dict item continuation
        if line.startswith("  ") and current_key is not None and ":" in line:
            if not isinstance(meta.get(current_key), dict):
                meta[current_key] = {}
            sub_k, sub_v = line.strip().split(":", 1)
            meta[current_key][sub_k.strip()] = _parse_yaml_value(sub_v.strip())
            continue

        # New key
        if ":" in line and not line.startswith(" "):
            current_list = None
            k, v = line.split(":", 1)
            current_key = k.strip()
            v_stripped = v.strip()
            if not v_stripped:
                # Value will come on following lines (list or dict)
                meta[current_key] = None
            else:
                meta[current_key] = _parse_yaml_value(v_stripped)

    return meta, body


def parse_sections(body: str) -> dict:
    """
    Parse ## Heading sections from markdown body.
    Returns ordered dict of {section_name: content_text}.
    """
    sections = {}
    current_section = None
    current_lines = []

    for line in body.splitlines():
        if line.startswith("## "):
            if current_section is not None:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = line[3:].strip()
            current_lines = []
        else:
            if current_section is not None:
                current_lines.append(line)

    if current_section is not None:
        sections[current_section] = "\n".join(current_lines).strip()

    return sections


def parse_memory_md(text: str) -> dict:
    """
    Parse a complete memory markdown document.
    Returns {"meta": {...}, "sections": {...}}.
    """
    meta, body = parse_frontmatter(text)
    sections = parse_sections(body)
    return {"meta": meta, "sections": sections}


def extract_links(meta: dict) -> list:
    """Get forward links from parsed meta."""
    v = meta.get("links", [])
    return v if isinstance(v, list) else []


def extract_backlinks(meta: dict) -> list:
    """Get backlinks from parsed meta."""
    v = meta.get("backlinked_by", [])
    return v if isinstance(v, list) else []
