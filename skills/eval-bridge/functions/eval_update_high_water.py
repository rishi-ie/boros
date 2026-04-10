
import os, json

def eval_update_high_water(params: dict, kernel=None) -> dict:
    """Update high-water marks — tracks the actual best score per category.
    
    High-water marks are the regression baseline. They must reflect the actual
    peak, not a dampened estimate. The regression checker's adaptive threshold
    already absorbs noise — the mark itself must be accurate.
    """
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
        if not isinstance(score, (int, float)):
            continue
        current_hw = high_water.get(cat, 0.0)
        
        if score > current_hw:
            high_water[cat] = round(score, 4)
            updated[cat] = {"old": current_hw, "new": high_water[cat]}

    with open(hw_file, "w") as f:
        json.dump(high_water, f, indent=2)

    return {"status": "ok", "updated_categories": updated, "high_water_marks": high_water}


