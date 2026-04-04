
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

    # Write request to shared directory for eval generator to pick up
    requests_dir = os.path.join(boros_dir, "eval-generator", "shared", "requests")
    os.makedirs(requests_dir, exist_ok=True)
    with open(os.path.join(requests_dir, f"{request_id}.json"), "w") as f:
        json.dump(request, f, indent=2)

    return {"status": "ok", "request_id": request_id, "message": "Evaluation request submitted to sandbox."}
