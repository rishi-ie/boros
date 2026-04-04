
import os, json, datetime
def evolve_modify_loop(params: dict, kernel=None) -> dict:
    """Record a proposed modification to the evolution loop parameters."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    record = {
        "modification": params.get("modification", ""),
        "rationale": params.get("rationale", ""),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "status": "proposed"
    }
    records_dir = os.path.join(boros_dir, "memory", "evolution_records")
    os.makedirs(records_dir, exist_ok=True)
    with open(os.path.join(records_dir, "loop_modifications.jsonl"), "a") as f:
        f.write(json.dumps(record) + "\n")
    return {"status": "ok", "record": record}
