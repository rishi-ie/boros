
import os, json, glob, time

_RESULTS_KEEP = 10  # how many raw result files to retain in eval-generator/shared/results/

def _prune_old_results(results_dir: str):
    """Keep only the most recent _RESULTS_KEEP result files. Older ones are already in
    score_history.jsonl and evals/scores/ so they can be safely deleted."""
    try:
        files = sorted(glob.glob(os.path.join(results_dir, "*.json")),
                       key=os.path.getmtime, reverse=True)
        for old in files[_RESULTS_KEEP:]:
            try:
                os.remove(old)
            except OSError:
                pass
    except Exception:
        pass

def _get_world_model_version(boros_dir: str) -> str:
    """Return version string from world_model.json for tagging score history entries."""
    try:
        wm_path = os.path.join(boros_dir, "world_model.json")
        with open(wm_path) as f:
            wm = json.load(f)
        categories = sorted(wm.get("categories", {}).keys())
        return f"{wm.get('version', '?')}:{','.join(categories)}"
    except Exception:
        return "unknown"

def eval_read_scores(params: dict, kernel=None) -> dict:
    """Read evaluation scores from the eval-generator results directory."""
    boros_dir = str(kernel.boros_root) if kernel else __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))))
    eval_id = params.get("eval_id", "")
    results_dir = os.path.join(boros_dir, "eval-generator", "shared", "results")

    wm_version = _get_world_model_version(boros_dir)

    def _rotate_score_history(score_hist):
        """Keep only the last MAX_HISTORY_LINES entries."""
        MAX_HISTORY_LINES = 500
        if not os.path.exists(score_hist):
            return
        try:
            with open(score_hist, "r") as f:
                lines = f.readlines()
            if len(lines) > MAX_HISTORY_LINES:
                archive = score_hist + ".archive"
                with open(archive, "a") as f:
                    f.writelines(lines[:-MAX_HISTORY_LINES])
                with open(score_hist, "w") as f:
                    f.writelines(lines[-MAX_HISTORY_LINES:])
        except Exception as e:
            print(f"[eval_read_scores] WARNING: could not rotate score history: {e}")

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
        entry = dict(result_data)
        entry["world_model_version"] = wm_version  # marks which world model generated this score
        with open(score_hist, "a") as f:
            f.write(json.dumps(entry) + "\n")
        _rotate_score_history(score_hist)

    def _copy_to_evals_scores(result_data):
        """Mirror result to evals/scores/ so agent_loop.py prompt injection works."""
        try:
            eval_scores_dir = os.path.join(boros_dir, "evals", "scores")
            os.makedirs(eval_scores_dir, exist_ok=True)
            eval_id_key = result_data.get("eval_id", result_data.get("request_id", "unknown"))
            dest = os.path.join(eval_scores_dir, f"{eval_id_key}.json")
            with open(dest, "w") as f:
                json.dump(result_data, f, indent=2)
        except Exception as e:
            print(f"[eval_read_scores] WARNING: could not mirror to evals/scores/: {e}")

    if eval_id:
        # Strip prefixes to handle LLM hallucinating req- vs eval- prefixes
        raw_id = eval_id.replace("req-", "").replace("eval-", "")

        # Also load the actual pending request ID from session (in case LLM hallucinated the ID)
        fallback_raw_id = None
        try:
            pending_path = os.path.join(boros_dir, "session", "pending_eval.json")
            if os.path.exists(pending_path):
                with open(pending_path) as f:
                    pending = json.load(f)
                fallback_raw_id = pending.get("request_id", "").replace("req-", "").replace("eval-", "")
        except Exception:
            pass

        # Read specific eval (wait up to 5 minutes)
        for attempt in range(60):
            for rf in glob.glob(os.path.join(results_dir, "*.json")):
                try:
                    with open(rf) as f:
                        result = json.load(f)
                        req_raw = result.get("request_id", "").replace("req-", "").replace("eval-", "")
                        ev_raw = result.get("eval_id", "").replace("req-", "").replace("eval-", "")
                        if raw_id == req_raw or raw_id == ev_raw or (fallback_raw_id and (fallback_raw_id == req_raw or fallback_raw_id == ev_raw)):
                            _append_to_history(result)
                            _copy_to_evals_scores(result)
                            # Clean up pending_eval.json once found
                            try:
                                pending_path = os.path.join(boros_dir, "session", "pending_eval.json")
                                if os.path.exists(pending_path):
                                    os.remove(pending_path)
                            except Exception:
                                pass
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
                    _copy_to_evals_scores(latest)
                    _prune_old_results(results_dir)
                    return {
                        "status": "ok",
                        "scores": latest.get("scores", {}),
                        "composite": latest.get("composite", 0),
                        "total_results": len(result_files),
                        "latest_eval_id": latest.get("eval_id", "")
                    }
        time.sleep(1)

    return {"status": "ok", "scores": {}, "composite": 0, "message": "No evaluation results found yet."}
