
import os, json, glob, sqlite3

def memory_search_sql(params: dict, kernel=None) -> dict:
    """Search memory using SQLite FTS when available, keyword grep as fallback."""
    boros_dir = str(kernel.boros_root) if kernel else os.getcwd()
    query = params.get("query", "").lower().strip()
    limit = params.get("limit", 20)

    if not query:
        return {"status": "error", "message": "query required"}

    results = []

    # ── Try SQLite FTS database first ─────────────────────────
    db_path = os.path.join(boros_dir, "memory", "memory.db")
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            # Check if FTS table exists
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "memories_fts" in tables:
                rows = conn.execute(
                    "SELECT m.id, m.entry_type, m.content, m.tags, m.timestamp "
                    "FROM memories m JOIN memories_fts fts ON m.id = fts.id "
                    "WHERE memories_fts MATCH ? LIMIT ?",
                    (query, limit)
                ).fetchall()
                for row in rows:
                    results.append({
                        "source": "sqlite_fts",
                        "id": row["id"],
                        "type": row["entry_type"],
                        "preview": row["content"][:300],
                        "tags": row["tags"],
                        "timestamp": row["timestamp"]
                    })
                conn.close()
                if results:
                    return {"status": "ok", "query": query, "matches": results, "total": len(results), "method": "sqlite_fts"}
            conn.close()
        except Exception as e:
            print(f"Memory search: SQLite FTS failed ({e}), falling back to file scan.")

    # ── Fallback: keyword scan over JSON/JSONL files ──────────
    memory_dir = os.path.join(boros_dir, "memory")
    if os.path.isdir(memory_dir):
        for root, dirs, files in os.walk(memory_dir):
            # Skip the SQLite db binary
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                if fname.endswith((".json", ".jsonl")):
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                            content = fh.read()
                        if query in content.lower():
                            results.append({
                                "source": "file_scan",
                                "file": os.path.relpath(fpath, memory_dir),
                                "preview": content[:300]
                            })
                    except OSError as e:
                        print(f"Memory search: could not read {fpath}: {e}")

    return {"status": "ok", "query": query, "matches": results[:limit], "total": len(results), "method": "file_scan"}
