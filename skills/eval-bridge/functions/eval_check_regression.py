
import os, json, datetime

def eval_check_regression(params: dict, kernel=None) -> dict:
    """Compare current scores against high-water marks. Auto-rollbacks on regression."""
    boros_dir = str(kernel.boros_root) if kernel else __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))))
    current_scores = params.get("current_scores", {})

    # Adaptive threshold: tighten as Boros matures
    cycle = 1
    cycle_file = os.path.join(boros_dir, "session", "current_cycle.json")
    if os.path.exists(cycle_file):
        try:
            with open(cycle_file) as f:
                cycle = json.load(f).get("cycle", 1)
        except Exception:
            pass
    if cycle <= 10:
        threshold = 0.05
    elif cycle <= 30:
        threshold = 0.03
    else:
        threshold = 0.02

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
    rollback_result = None

    if has_regression:
        # Auto-rollback: read snapshot_id from evolution_target written by forge_snapshot
        target_file = os.path.join(boros_dir, "session", "evolution_target.json")
        snapshot_id = None
        skill_name = None
        if os.path.exists(target_file):
            try:
                with open(target_file) as f:
                    target = json.load(f)
                snapshot_id = target.get("snapshot_id")
                skill_name = target.get("target_skill")
            except Exception:
                pass

        if snapshot_id and kernel and "evolve_rollback" in kernel.registry:
            rollback_result = kernel.registry["evolve_rollback"](
                {"snapshot_id": snapshot_id, "target": skill_name}, kernel
            )
            # Log the auto-rollback
            try:
                records_dir = os.path.join(boros_dir, "memory", "evolution_records")
                os.makedirs(records_dir, exist_ok=True)
                log_entry = {
                    "event": "auto_rollback",
                    "cycle": cycle,
                    "snapshot_id": snapshot_id,
                    "skill_name": skill_name,
                    "regressions": regressions,
                    "threshold_used": threshold,
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
                }
                log_path = os.path.join(records_dir, f"rollback-cycle{cycle}.json")
                with open(log_path, "w") as f:
                    json.dump(log_entry, f, indent=2)
            except Exception as e:
                print(f"[eval_check_regression] WARNING: could not log rollback: {e}")
        else:
            rollback_result = {"status": "skipped", "reason": "No snapshot_id in evolution_target — cannot auto-rollback"}

    return {
        "status": "ok",
        "has_regression": has_regression,
        "regressions": regressions,
        "improvements": improvements,
        "threshold_used": threshold,
        "auto_rollback": rollback_result,
        "message": (
            f"AUTO-ROLLED BACK — regressions detected in {list(regressions.keys())}. Snapshot restored."
            if has_regression and rollback_result and rollback_result.get("status") == "ok"
            else "No regressions. Safe to commit." if not has_regression
            else f"REGRESSION detected but rollback skipped: {rollback_result}"
        )
    }
