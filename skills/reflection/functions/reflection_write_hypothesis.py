
import os, json, uuid, datetime
def reflection_write_hypothesis(params: dict, kernel=None) -> dict:
    """Write an improvement hypothesis for this cycle."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    hyp_id = f"hyp-{uuid.uuid4().hex[:8]}"
    hyp = {
        "id": hyp_id,
        "rationale": params.get("rationale", ""),
        "target_skill": params.get("target_skill", ""),
        "expected_improvement": params.get("expected_improvement", ""),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }
    os.makedirs(os.path.join(boros_dir, "session"), exist_ok=True)
    with open(os.path.join(boros_dir, "session", "hypothesis.json"), "w") as f:
        json.dump(hyp, f, indent=2)

    return {"status": "ok", "hypothesis_id": hyp_id}
