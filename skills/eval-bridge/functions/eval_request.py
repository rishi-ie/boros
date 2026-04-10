
import os, json, uuid, datetime
def eval_request(params: dict, kernel=None) -> dict:
    """Submit an evaluation request to the Eval Generator sandbox."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    request_id = f"req-{uuid.uuid4().hex[:8]}"
    cycle = params.get("cycle", 0)
    categories = params.get("categories", [])

    request = {
        "request_id": request_id,
        "cycle": cycle,
        "categories": categories,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }

    # Check eval-generator heartbeat (warn if not running or stale)
    ready_file = os.path.join(boros_dir, "eval-generator", "shared", ".ready")
    is_alive = False
    import time
    if os.path.exists(ready_file):
        try:
            mtime = os.path.getmtime(ready_file)
            if time.time() - mtime < 300: # 5 minutes heartbeat
                is_alive = True
        except OSError:
            pass

    if not is_alive:
        return {
            "status": "error",
            "message": (
                "Eval-generator is not responding (no heartbeat in 5 minutes). Start or restart it first:\n"
                "  python eval-generator/eval_generator.py\n"
                "Or use start.py to launch both processes together:\n"
                "  python start.py"
            )
        }

    # Write request to shared directory for eval generator to pick up
    requests_dir = os.path.join(boros_dir, "eval-generator", "shared", "requests")
    os.makedirs(requests_dir, exist_ok=True)
    with open(os.path.join(requests_dir, f"{request_id}.json"), "w") as f:
        json.dump(request, f, indent=2)

    # Track pending request in session so eval_read_scores can find it even if LLM hallucinates the ID
    session_dir = os.path.join(boros_dir, "session")
    os.makedirs(session_dir, exist_ok=True)
    with open(os.path.join(session_dir, "pending_eval.json"), "w") as f:
        json.dump({"request_id": request_id, "timestamp": request["timestamp"]}, f)

    return {"status": "ok", "request_id": request_id, "message": f"Evaluation request submitted. Use eval_id='{request_id}' when calling eval_read_scores."}
