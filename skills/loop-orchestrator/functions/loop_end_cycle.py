
import os, json, datetime, uuid
def loop_end_cycle(params: dict, kernel=None) -> dict:
    boros_dir = str(kernel.boros_root) if kernel else "boros"

    state_file = os.path.join(boros_dir, "session", "loop_state.json")
    if os.path.exists(state_file):
        with open(state_file) as f:
            state = json.load(f)
        cycle = state.get("cycle", 1)
        state["stage"] = None
        state["cycle_ended_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
    else:
        cycle = 0

    # ── Archive hypothesis with outcome before clearing session ──────────────
    hyp_file = os.path.join(boros_dir, "session", "hypothesis.json")
    hypothesis_archived = False
    if os.path.exists(hyp_file):
        try:
            with open(hyp_file) as f:
                hypothesis = json.load(f)

            # Read score history to compute before/after delta
            score_hist_path = os.path.join(boros_dir, "memory", "score_history.jsonl")
            score_before, score_after, outcome = {}, {}, "unknown"
            if os.path.exists(score_hist_path):
                with open(score_hist_path) as f:
                    lines = [ln for ln in f if ln.strip()]
                entries = [json.loads(l) for l in lines]
                # Find the two most recent entries that have scores
                scored = [e for e in entries if e.get("scores")]
                if len(scored) >= 2:
                    score_before = scored[-2].get("scores", {})
                    score_after  = scored[-1].get("scores", {})
                elif len(scored) == 1:
                    score_after = scored[-1].get("scores", {})

            # Determine outcome: check the target category
            target_cat = hypothesis.get("target_skill", "")
            # Try to find the category that matches the target skill
            before_val = None
            after_val  = None
            for cat, val in score_after.items():
                if cat in target_cat or target_cat in cat:
                    after_val = val
                    before_val = score_before.get(cat)
                    break
            if before_val is not None and after_val is not None:
                delta = after_val - before_val
                if delta > 0.02:
                    outcome = "improved"
                elif delta < -0.02:
                    outcome = "regressed"
                else:
                    outcome = "neutral"
            elif after_val is not None:
                outcome = "baseline"

            score_delta = None
            if before_val is not None and after_val is not None:
                score_delta = round(after_val - before_val, 4)

            archive_entry = {
                "id": hypothesis.get("id", f"hyp-{uuid.uuid4().hex[:8]}"),
                "cycle": cycle,
                "target_skill": hypothesis.get("target_skill", ""),
                "rationale": hypothesis.get("rationale", ""),
                "expected_improvement": hypothesis.get("expected_improvement", ""),
                "actual_outcome": outcome,
                "score_delta": score_delta,
                "score_before": score_before,
                "score_after": score_after,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }

            records_dir = os.path.join(boros_dir, "memory", "evolution_records")
            os.makedirs(records_dir, exist_ok=True)
            archive_path = os.path.join(records_dir, f"hyp-cycle{cycle}.json")
            with open(archive_path, "w") as f:
                json.dump(archive_entry, f, indent=2)
            hypothesis_archived = True
        except Exception as e:
            print(f"[loop_end_cycle] WARNING: hypothesis archival failed: {e}")

    # Auto-update high-water marks from latest scores
    hw_updated = {}
    score_hist = os.path.join(boros_dir, "memory", "score_history.jsonl")
    if os.path.exists(score_hist):
        try:
            with open(score_hist, "r") as f:
                lines = [ln for ln in f if ln.strip()]
            if lines:
                latest = json.loads(lines[-1])
                latest_scores = latest.get("scores", {})
                if latest_scores and kernel and "eval_update_high_water" in kernel.registry:
                    result = kernel.registry["eval_update_high_water"]({"scores": latest_scores}, kernel)
                    hw_updated = result.get("updated_categories", {})
        except Exception as e:
            print(f"[loop_end_cycle] WARNING: high-water mark update failed: {e}")

    # Check milestone advancement after high-water marks are updated
    if kernel and "eval_check_milestone" in kernel.registry:
        try:
            milestone_result = kernel.registry["eval_check_milestone"]({}, kernel)
            if milestone_result.get("advanced"):
                print(f"[loop_end_cycle] Milestones advanced: {milestone_result['advanced']}")
        except Exception as e:
            print(f"[loop_end_cycle] WARNING: milestone check failed: {e}")

    # Clean up session artifacts — hypothesis.json is intentionally NOT kept
    session_dir = os.path.join(boros_dir, "session")
    keep = {"loop_state.json", "current_cycle.json", "evolution_target.json"}
    if os.path.isdir(session_dir):
        for item in os.listdir(session_dir):
            if item not in keep and not os.path.isdir(os.path.join(session_dir, item)):
                try:
                    os.remove(os.path.join(session_dir, item))
                except OSError:
                    pass

    # Log
    log_file = os.path.join(boros_dir, "logs", "cycles.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, "a") as f:
        f.write(f"Cycle {cycle} ended at {datetime.datetime.utcnow().isoformat()}Z\n")

    return {
        "status": "ok",
        "cycle": cycle,
        "message": f"Cycle {cycle} complete.",
        "high_water_updated": hw_updated,
        "hypothesis_archived": hypothesis_archived
    }
