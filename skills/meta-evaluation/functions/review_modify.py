
import os, json, datetime
def review_modify(params: dict, kernel=None) -> dict:
    """Record modification request for a proposal."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    record = {
        "proposal_id": params.get("proposal_id", ""),
        "modifications": params.get("modifications", ""),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }
    records_dir = os.path.join(boros_dir, "memory", "evolution_records")
    os.makedirs(records_dir, exist_ok=True)
    with open(os.path.join(records_dir, f"modify-{record['proposal_id']}.json"), "w") as f:
        json.dump(record, f, indent=2)
    return {"status": "ok", "record": record}
