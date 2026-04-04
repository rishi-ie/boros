
import os, json, glob, time
def eval_read_scores(params: dict, kernel=None) -> dict:
    """Read evaluation scores from the eval-generator results directory."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    eval_id = params.get("eval_id", "")
    results_dir = os.path.join(boros_dir, "eval-generator", "shared", "results")

    def _append_to_history(result_data):
        score_hist = os.path.join(boros_dir, "memory", "score_history.jsonl")
        os.makedirs(os.path.dirname(score_hist), exist_ok=True)
        # Check if already the last entry
        if os.path.exists(score_hist):
            try:
                with open(score_hist, "r") as f:
                    lines = [ln for ln in f if ln.strip()]
                    if lines:
                        last_entry = json.loads(lines[-1])
                        if last_entry.get("eval_id") == result_data.get("eval_id"):
                            return # Already appended
            except Exception:
                pass
        with open(score_hist, "a") as f:
            f.write(json.dumps(result_data) + "\n")

    if eval_id:
        # Strip prefixes to handle LLM hallucinating req- vs eval- prefixes
        raw_id = eval_id.replace("req-", "").replace("eval-", "")
        # Read specific eval (wait up to 5 minutes)
        for attempt in range(60):
            for rf in glob.glob(os.path.join(results_dir, "*.json")):
                try:
                    with open(rf) as f:
                        result = json.load(f)
                        req_raw = result.get("request_id", "").replace("req-", "").replace("eval-", "")
                        ev_raw = result.get("eval_id", "").replace("req-", "").replace("eval-", "")
                        if raw_id == req_raw or raw_id == ev_raw:
                            _append_to_history(result)
                            return {"status": "ok", "scores": result.get("scores", {}), "composite": result.get("composite", 0), "result": result}
                except Exception:
                    pass
            time.sleep(5)
        return {"status": "error", "message": f"Timeout waiting for evaluation results for {eval_id}"}


    # Read latest results (poll briefly if no results yet)
    for attempt in range(3):
        if os.path.isdir(results_dir):
            result_files = sorted(glob.glob(os.path.join(results_dir, "*.json")), key=os.path.getmtime, reverse=True)
            if result_files:
                results = []
                for rf in result_files[:5]:
                    try:
                        with open(rf) as f:
                            results.append(json.load(f))
                    except Exception:
                        pass
                if results:
                    latest = results[0]
                    # Check if we already have this in history
                    score_hist = os.path.join(boros_dir, "memory", "score_history.jsonl")
                    if os.path.exists(score_hist):
                        try:
                            with open(score_hist, "r") as f:
                                lines = [ln for ln in f if ln.strip()]
                                if lines:
                                    last_entry = json.loads(lines[-1])
                                    if last_entry.get("eval_id") == latest.get("eval_id"):
                                        return {
                                            "status": "ok", 
                                            "message": "Returned latest evaluation results (already in score history).",
                                            "scores": latest.get("scores", {}),
                                            "composite": latest.get("composite", 0),
                                            "latest_eval_id": latest.get("eval_id", "")
                                        }
                        except Exception:
                            pass
                    
                    _append_to_history(latest)
                    return {
                        "status": "ok",
                        "scores": latest.get("scores", {}),
                        "composite": latest.get("composite", 0),
                        "total_results": len(result_files),
                        "latest_eval_id": latest.get("eval_id", "")
                    }
        time.sleep(1)

    return {"status": "ok", "scores": {}, "composite": 0, "message": "No evaluation results found yet."}
