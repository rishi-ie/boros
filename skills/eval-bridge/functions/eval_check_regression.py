
import os, json
def eval_check_regression(params: dict, kernel=None) -> dict:
    """Compare current scores against high-water marks to detect regressions."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    current_scores = params.get("current_scores", {})
    threshold = params.get("threshold", 0.05)

    hw_file = os.path.join(boros_dir, "skills", "eval-bridge", "state", "high_water_marks.json")
    high_water = {}
    if os.path.exists(hw_file):
        with open(hw_file) as f:
            high_water = json.load(f)

    regressions = {}
    improvements = {}
    for cat, score in current_scores.items():
        if isinstance(score, (int, float)):
            hw = high_water.get(cat, 0)
            if score < hw - threshold:
                regressions[cat] = {"current": score, "high_water": hw, "delta": round(score - hw, 4)}
            elif score > hw:
                improvements[cat] = {"current": score, "high_water": hw, "delta": round(score - hw, 4)}

    has_regression = len(regressions) > 0
    return {
        "status": "ok",
        "has_regression": has_regression,
        "regressions": regressions,
        "improvements": improvements,
        "recommendation": "ROLLBACK recommended — regressions detected." if has_regression else "No regressions. Safe to proceed."
    }
