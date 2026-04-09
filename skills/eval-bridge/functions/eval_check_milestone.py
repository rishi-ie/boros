import os, json, datetime

def eval_check_milestone(params: dict, kernel=None) -> dict:
    """Check if any category has cleared its current milestone and should advance.

    After each eval, reads score_history.jsonl to see if the current milestone's
    unlock_score has been sustained for unlock_consecutive evals. If so, advances
    current_milestone in world_model.json and logs the advancement.

    Returns a dict of any categories that advanced, plus current milestone status.
    """
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    wm_path   = os.path.join(boros_dir, "world_model.json")
    progress_path = os.path.join(boros_dir, "skills", "eval-bridge", "state", "milestone_progress.json")
    score_hist    = os.path.join(boros_dir, "memory", "score_history.jsonl")

    if not os.path.exists(wm_path):
        return {"status": "error", "message": "world_model.json not found"}

    with open(wm_path) as f:
        wm = json.load(f)

    # Load or initialise milestone progress tracker
    progress = {}
    if os.path.exists(progress_path):
        try:
            with open(progress_path) as f:
                progress = json.load(f)
        except Exception:
            progress = {}

    # Read recent score history — last 10 entries is enough
    recent_scores = []
    if os.path.exists(score_hist):
        with open(score_hist) as f:
            lines = [l.strip() for l in f if l.strip()]
        for line in lines[-10:]:
            try:
                recent_scores.append(json.loads(line))
            except Exception:
                pass

    advanced    = {}
    status_info = {}
    wm_changed  = False

    for cat_id, cat_data in wm.get("categories", {}).items():
        milestones = cat_data.get("milestones", [])
        if not milestones:
            continue  # flat-format category — no milestone advancement

        current_idx = cat_data.get("current_milestone", 0)
        if current_idx >= len(milestones):
            status_info[cat_id] = {"status": "maxed_out", "milestone": current_idx}
            continue

        m = milestones[current_idx]
        unlock_score       = m.get("unlock_score", 0.75)
        unlock_consecutive = m.get("unlock_consecutive", 2)

        # Count how many of the most recent evals for this category hit unlock_score
        cat_scores = []
        for entry in recent_scores:
            score = entry.get("scores", {}).get(cat_id)
            if score is not None:
                cat_scores.append(float(score))

        # Look at the last `unlock_consecutive` scores
        window = cat_scores[-unlock_consecutive:] if len(cat_scores) >= unlock_consecutive else []
        consecutive_cleared = len(window) == unlock_consecutive and all(s >= unlock_score for s in window)

        if consecutive_cleared:
            next_idx = current_idx + 1
            if next_idx < len(milestones):
                # Advance milestone
                wm["categories"][cat_id]["current_milestone"] = next_idx
                wm_changed = True

                # Log advancement
                records_dir = os.path.join(boros_dir, "memory", "evolution_records")
                os.makedirs(records_dir, exist_ok=True)
                log_entry = {
                    "event":             "milestone_advanced",
                    "category":          cat_id,
                    "from_milestone":    current_idx,
                    "to_milestone":      next_idx,
                    "milestone_name":    milestones[next_idx].get("name", f"Level {next_idx}"),
                    "unlock_scores":     window,
                    "timestamp":         datetime.datetime.utcnow().isoformat() + "Z"
                }
                ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                with open(os.path.join(records_dir, f"milestone-{cat_id}-L{next_idx}-{ts}.json"), "w") as f:
                    json.dump(log_entry, f, indent=2)

                advanced[cat_id] = {
                    "from": current_idx,
                    "to":   next_idx,
                    "new_milestone_name": milestones[next_idx].get("name")
                }
                # Reset consecutive counter for new milestone
                progress[cat_id] = {"consecutive": 0, "milestone": next_idx}
            else:
                status_info[cat_id] = {"status": "maxed_out", "milestone": current_idx, "scores": window}
        else:
            # Update consecutive counter
            consecutive_so_far = sum(1 for s in reversed(cat_scores) if s >= unlock_score)
            progress[cat_id] = {
                "milestone":        current_idx,
                "consecutive":      len(window),
                "needed":           unlock_consecutive,
                "recent_scores":    cat_scores[-5:],
                "unlock_score":     unlock_score
            }
            status_info[cat_id] = progress[cat_id]

    # Write back world_model.json if any milestone advanced
    if wm_changed:
        with open(wm_path, "w") as f:
            json.dump(wm, f, indent=2)

    # Persist progress tracker
    os.makedirs(os.path.dirname(progress_path), exist_ok=True)
    with open(progress_path, "w") as f:
        json.dump(progress, f, indent=2)

    return {
        "status":   "ok",
        "advanced": advanced,
        "category_status": status_info,
        "message":  (
            f"Advanced milestones: {list(advanced.keys())}" if advanced
            else "No milestones advanced this cycle."
        )
    }
