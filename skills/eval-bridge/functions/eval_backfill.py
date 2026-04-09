
import os, json, glob
def eval_backfill(params: dict, kernel=None) -> dict:
    """Backfill missing scores into score_history from eval results.
    Writes full entries (eval_id, cycle, timestamp, scores, composite) to preserve format."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    cycle = params.get("cycle", 0)

    results_dir = os.path.join(boros_dir, "eval-generator", "shared", "results")
    score_hist = os.path.join(boros_dir, "memory", "score_history.jsonl")
    os.makedirs(os.path.dirname(score_hist), exist_ok=True)

    # Load existing eval_ids to avoid duplicates
    existing_ids = set()
    if os.path.exists(score_hist):
        with open(score_hist) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        eid = entry.get("eval_id") or entry.get("request_id")
                        if eid:
                            existing_ids.add(eid)
                    except Exception:
                        pass

    count = 0
    if os.path.isdir(results_dir):
        for rf in glob.glob(os.path.join(results_dir, "*.json")):
            try:
                with open(rf) as f:
                    result = json.load(f)
                if result.get("cycle", -1) != cycle:
                    continue
                eval_id = result.get("eval_id") or result.get("request_id", "")
                if eval_id in existing_ids:
                    continue
                # Write a full, correctly-formatted entry
                entry = {
                    "eval_id":   eval_id,
                    "cycle":     result.get("cycle", cycle),
                    "timestamp": result.get("timestamp", ""),
                    "scores":    result.get("scores", {}),
                    "composite": result.get("composite", 0)
                }
                with open(score_hist, "a") as f:
                    f.write(json.dumps(entry) + "\n")
                existing_ids.add(eval_id)
                count += 1
            except Exception:
                pass
    return {"status": "ok", "records_backfilled": count}
