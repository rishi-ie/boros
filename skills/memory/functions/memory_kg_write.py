
import os, json, sqlite3, datetime

def memory_kg_write(params: dict, kernel=None) -> dict:
    """Record a temporal fact about a skill or category in the knowledge graph.

    Stores subject-predicate-object triples with validity windows so you can
    query what was true at a specific cycle, not just right now.

    Common predicates:
      has_score         — "reasoning" has_score "0.72" at cycle 5
      was_modified      — "reasoning" was_modified "reflection.py" at cycle 5
      achieved_milestone — "reasoning" achieved_milestone "L1" at cycle 12
      caused_delta_in   — "reasoning" caused_delta_in "web_search:+0.01" at cycle 5
      target_of         — "reflection" target_of "hypothesis-abc" at cycle 5
    """
    boros_dir = str(kernel.boros_root) if kernel else os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )

    subject   = str(params.get("subject", "")).strip()
    predicate = str(params.get("predicate", "")).strip()
    obj       = str(params.get("object", "")).strip()

    if not subject or not predicate or not obj:
        return {"status": "error", "message": "subject, predicate, and object are all required"}

    cycle      = params.get("cycle")
    valid_from = params.get("valid_from") or datetime.datetime.utcnow().isoformat() + "Z"
    metadata   = params.get("metadata")
    metadata_str = json.dumps(metadata) if metadata else None

    db_path = os.path.join(boros_dir, "memory", "memory.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    try:
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kg_triples (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                subject    TEXT NOT NULL,
                predicate  TEXT NOT NULL,
                object     TEXT NOT NULL,
                valid_from TEXT NOT NULL,
                valid_until TEXT,
                cycle      INTEGER,
                metadata   TEXT
            )
        """)
        cursor = conn.execute(
            "INSERT INTO kg_triples (subject, predicate, object, valid_from, valid_until, cycle, metadata) "
            "VALUES (?, ?, ?, ?, NULL, ?, ?)",
            (subject, predicate, obj, valid_from, cycle, metadata_str)
        )
        triple_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {"status": "ok", "triple_id": triple_id, "subject": subject, "predicate": predicate, "object": obj}
    except Exception as e:
        return {"status": "error", "message": f"KG write failed: {e}"}
