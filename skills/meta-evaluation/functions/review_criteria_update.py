
import os, json
def review_criteria_update(params: dict, kernel=None) -> dict:
    """Update the review criteria used by the Meta-Evaluation board."""
    boros_dir = str(kernel.boros_root) if kernel else __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))))
    criteria = params.get("criteria", {})
    criteria_file = os.path.join(boros_dir, "skills", "meta-evaluation", "state", "criteria.json")
    os.makedirs(os.path.dirname(criteria_file), exist_ok=True)

    existing = {}
    if os.path.exists(criteria_file):
        with open(criteria_file) as f:
            existing = json.load(f)
    existing.update(criteria)
    with open(criteria_file, "w") as f:
        json.dump(existing, f, indent=2)
    return {"status": "ok", "criteria": existing}
