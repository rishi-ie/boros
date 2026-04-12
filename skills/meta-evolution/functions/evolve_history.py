
import os, json, glob
def evolve_history(params: dict, kernel=None) -> dict:
    """Read evolution history from memory/evolution_records."""
    boros_dir = str(kernel.boros_root) if kernel else __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))))
    limit = params.get("limit", 10)
    records_dir = os.path.join(boros_dir, "memory", "evolution_records")
    records = []
    if os.path.isdir(records_dir):
        files = sorted(glob.glob(os.path.join(records_dir, "*.json")), key=os.path.getmtime, reverse=True)
        for rf in files[:limit]:
            try:
                with open(rf) as f:
                    records.append(json.load(f))
            except Exception:
                pass
    return {"status": "ok", "records": records, "total": len(records)}
