
import os, json, uuid, datetime, sqlite3

def memory_commit_archival(params: dict, kernel=None) -> dict:
    """Commit an entry to long-term archival memory. Writes to both file store and SQLite FTS."""
    boros_dir = str(kernel.boros_root) if kernel else os.getcwd()
    entry_type = params.get("entry_type", "observation")
    content = params.get("content", "")
    tags = params.get("tags", [])

    if not content:
        return {"status": "error", "message": "content required"}

    entry_id = f"exp-{uuid.uuid4().hex[:8]}"
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    tags_str = json.dumps(tags)

    entry = {
        "id": entry_id,
        "entry_type": entry_type,
        "content": content,
        "tags": tags,
        "timestamp": timestamp
    }

    # ── Write to file store ────────────────────────────────────
    exp_dir = os.path.join(boros_dir, "memory", "experiences")
    os.makedirs(exp_dir, exist_ok=True)
    try:
        with open(os.path.join(exp_dir, f"{entry_id}.json"), "w") as f:
            json.dump(entry, f, indent=2)
    except OSError as e:
        return {"status": "error", "message": f"Failed to write memory file: {e}"}

    # ── Write to SQLite with FTS for fast search ───────────────
    db_path = os.path.join(boros_dir, "memory", "memory.db")
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                entry_type TEXT,
                content TEXT,
                tags TEXT,
                timestamp TEXT
            )
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(id, content, tags, content='memories', content_rowid='rowid')
        """)
        conn.execute(
            "INSERT OR REPLACE INTO memories (id, entry_type, content, tags, timestamp) VALUES (?,?,?,?,?)",
            (entry_id, entry_type, content, tags_str, timestamp)
        )
        conn.execute(
            "INSERT INTO memories_fts (id, content, tags) VALUES (?,?,?)",
            (entry_id, content, tags_str)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Memory: SQLite write failed ({e}) — file store write succeeded.")

    return {"status": "ok", "entry_id": entry_id, "entry_type": entry_type, "timestamp": timestamp}
