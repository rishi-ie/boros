
import os, json
def eval_update_high_water(params: dict, kernel=None) -> dict:
    """Update high-water marks if current scores exceed them."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    scores = params.get("scores", {})

    hw_file = os.path.join(boros_dir, "skills", "eval-bridge", "state", "high_water_marks.json")
    os.makedirs(os.path.dirname(hw_file), exist_ok=True)

    high_water = {}
    if os.path.exists(hw_file):
        with open(hw_file) as f:
            high_water = json.load(f)

    updated = {}
    for cat, score in scores.items():
        if isinstance(score, (int, float)):
            if score > high_water.get(cat, 0):
                high_water[cat] = score
                updated[cat] = score

    with open(hw_file, "w") as f:
        json.dump(high_water, f, indent=2)

    return {"status": "ok", "updated_categories": updated, "high_water_marks": high_water}
