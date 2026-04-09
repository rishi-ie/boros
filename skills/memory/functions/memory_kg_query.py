
import os, json, sqlite3

def memory_kg_query(params: dict, kernel=None) -> dict:
    """Query current or historical facts about a skill or category from the knowledge graph.

    Returns facts that are currently valid (valid_until IS NULL) by default.
    Pass include_history=True to also see invalidated/past facts.
    Pass as_of=<ISO timestamp> to see what was true at a specific point in time.

    Examples:
      memory_kg_query({"subject": "reasoning"})
        → all current facts about the reasoning category

      memory_kg_query({"subject": "reasoning", "predicate": "has_score"})
        → all score facts for reasoning (current)

      memory_kg_query({"subject": "reflection", "include_history": true})
        → full history: every fact ever recorded about the reflection skill

      memory_kg_query({"subject": "reasoning", "as_of": "2026-04-01T00:00:00Z"})
        → what was true about reasoning on April 1st
    """
    boros_dir = str(kernel.boros_root) if kernel else os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )

    subject         = str(params.get("subject", "")).strip()
    predicate_filter = params.get("predicate", "").strip()
    as_of           = params.get("as_of", "")
    include_history = bool(params.get("include_history", False))

    if not subject:
        return {"status": "error", "message": "subject is required"}

    db_path = os.path.join(boros_dir, "memory", "memory.db")
    if not os.path.exists(db_path):
        return {"status": "ok", "subject": subject, "facts": [], "note": "No knowledge graph yet"}

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Check table exists
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "kg_triples" not in tables:
            conn.close()
            return {"status": "ok", "subject": subject, "facts": [], "note": "No knowledge graph yet"}

        if as_of:
            # What was true at as_of: valid_from <= as_of AND (valid_until IS NULL OR valid_until > as_of)
            query = "SELECT * FROM kg_triples WHERE subject=? AND valid_from <= ? AND (valid_until IS NULL OR valid_until > ?)"
            args = [subject, as_of, as_of]
        elif include_history:
            query = "SELECT * FROM kg_triples WHERE subject=?"
            args = [subject]
        else:
            # Only currently valid (valid_until IS NULL)
            query = "SELECT * FROM kg_triples WHERE subject=? AND valid_until IS NULL"
            args = [subject]

        if predicate_filter:
            query += " AND predicate=?"
            args.append(predicate_filter)

        query += " ORDER BY valid_from DESC"

        rows = conn.execute(query, args).fetchall()
        conn.close()

        facts = []
        for row in rows:
            fact = {
                "id":          row["id"],
                "predicate":   row["predicate"],
                "object":      row["object"],
                "valid_from":  row["valid_from"],
                "valid_until": row["valid_until"],
                "cycle":       row["cycle"],
            }
            if row["metadata"]:
                try:
                    fact["metadata"] = json.loads(row["metadata"])
                except Exception:
                    fact["metadata"] = row["metadata"]
            facts.append(fact)

        return {"status": "ok", "subject": subject, "facts": facts, "count": len(facts)}
    except Exception as e:
        return {"status": "error", "message": f"KG query failed: {e}"}
