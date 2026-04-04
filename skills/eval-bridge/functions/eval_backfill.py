
import os, json
def eval_backfill(params: dict, kernel=None) -> dict:
    """Backfill missing scores into score_history from eval results."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    cycle = params.get("cycle", 0)
    import glob, time

    results_dir = os.path.join(boros_dir, "eval-generator", "shared", "results")
    score_hist = os.path.join(boros_dir, "memory", "score_history.jsonl")
    os.makedirs(os.path.dirname(score_hist), exist_ok=True)

    count = 0
    if os.path.isdir(results_dir):
        for rf in glob.glob(os.path.join(results_dir, "*.json")):
            try:
                with open(rf) as f:
                    result = json.load(f)
                if result.get("cycle", -1) == cycle:
                    with open(score_hist, "a") as f:
                        f.write(json.dumps(result.get("scores", {})) + "\n")
                    count += 1
            except Exception:
                pass
    return {"status": "ok", "records_updated": count}
