
import os, json

def eval_update_high_water(params: dict, kernel=None) -> dict:
    """Update high-water marks using EMA (exponential moving average) dampening.
    
    FIX-12: Instead of absolute maximum (which ratchets to noise spikes),
    blend toward new highs and allow slow decay when consistently below.
    """
    ALPHA = 0.7   # Weight of new score vs. existing high-water (0-1)
    DECAY = 0.01  # Decay rate per cycle when consistently below mark

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
            if current_hw == 0.0:
                # First time establishing a baseline; no dampening
                new_hw = score
            else:
                # Dampen: don't jump to the spike, blend toward it
                new_hw = current_hw * (1 - ALPHA) + score * ALPHA
                
            high_water[cat] = round(new_hw, 4)
            updated[cat] = {"old": current_hw, "new": high_water[cat], "action": "baseline" if current_hw == 0.0 else "ema_blend"}
        elif score < current_hw - 0.1:
            # Significantly below mark — allow slow decay
            new_hw = round(max(score, current_hw - DECAY), 4)
            if new_hw < current_hw:
                high_water[cat] = new_hw
                updated[cat] = {"old": current_hw, "new": new_hw, "action": "decay"}

    with open(hw_file, "w") as f:
        json.dump(high_water, f, indent=2)

    return {"status": "ok", "updated_categories": updated, "high_water_marks": high_water}

