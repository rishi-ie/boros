
import os, json, glob
def review_history(params: dict, kernel=None) -> dict:
    """Read past review decisions."""
    boros_dir = str(kernel.boros_root) if kernel else __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))))
    limit = params.get("limit", 10)
    records_dir = os.path.join(boros_dir, "memory", "evolution_records")
    reviews = []
    if os.path.isdir(records_dir):
        for rf in sorted(glob.glob(os.path.join(records_dir, "review-*.json")), key=os.path.getmtime, reverse=True)[:limit]:
            try:
                with open(rf) as f:
                    reviews.append(json.load(f))
            except Exception:
                pass
    return {"status": "ok", "reviews": reviews}
