
import os, json, glob
def memory_search_sql(params: dict, kernel=None) -> dict:
    """Search memory files using keyword matching."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    query = params.get("query", "").lower()
    if not query:
        return {"status": "error", "message": "query required"}
    results = []
    memory_dir = os.path.join(boros_dir, "memory")
    if os.path.isdir(memory_dir):
        for root, dirs, files in os.walk(memory_dir):
            for fname in files:
                if fname.endswith((".json", ".jsonl")):
                    fpath = os.path.join(root, fname)
                    try:
                        content = open(fpath, "r").read()
                        if query in content.lower():
                            results.append({"file": os.path.relpath(fpath, memory_dir), "preview": content[:300]})
                    except: pass
    return {"status": "ok", "query": query, "matches": results[:20], "total": len(results)}
