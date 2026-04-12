"""
Maintains bidirectional links between memory nodes.
When node A declares links: [B, C], this writes A into B.backlinked_by and C.backlinked_by.
Call update_backlinks() at write time, after the source node is persisted.
"""

import os
from .md_parser import parse_memory_md, extract_links, extract_backlinks
from .md_writer import build_memory_md
from .index_manager import SECTIONS, get_node_path


def _find_node_path(boros_dir: str, target_id: str) -> str | None:
    """Search all sections for a node by ID. Returns path or None."""
    for sec in SECTIONS:
        path = get_node_path(boros_dir, sec, target_id)
        if os.path.exists(path):
            return path
    return None


def _add_backlink(boros_dir: str, target_id: str, source_id: str):
    """
    Add source_id to target_id's backlinked_by list.
    No-op if already present or target not found.
    """
    path = _find_node_path(boros_dir, target_id)
    if not path or not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    parsed = parse_memory_md(content)
    meta = parsed["meta"]
    sections = parsed["sections"]

    backlinks = extract_backlinks(meta)
    if source_id in backlinks:
        return  # Already registered

    backlinks.append(source_id)
    meta["backlinked_by"] = backlinks

    new_content = build_memory_md(meta, sections)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)


def _remove_backlink(boros_dir: str, target_id: str, source_id: str):
    """Remove source_id from target_id's backlinked_by list."""
    path = _find_node_path(boros_dir, target_id)
    if not path or not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    parsed = parse_memory_md(content)
    meta = parsed["meta"]
    sections = parsed["sections"]

    backlinks = extract_backlinks(meta)
    if source_id not in backlinks:
        return

    meta["backlinked_by"] = [b for b in backlinks if b != source_id]
    new_content = build_memory_md(meta, sections)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)


def update_backlinks(boros_dir: str, node_id: str, new_links: list,
                     old_links: list = None):
    """
    Reconcile backlinks after a node is written.
    - Adds backlink to each newly added link target
    - Removes backlink from each removed link target
    """
    old = set(old_links or [])
    new = set(new_links or [])

    for added in (new - old):
        _add_backlink(boros_dir, added, node_id)

    for removed in (old - new):
        _remove_backlink(boros_dir, removed, node_id)
