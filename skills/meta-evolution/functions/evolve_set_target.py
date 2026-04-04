
import os, json, datetime
def evolve_set_target(params: dict, kernel=None) -> dict:
    """Set the evolution target for this cycle. Writes to session."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    target = {
        "target_skill": params.get("target", params.get("target_skill", "")),
        "category": params.get("category", ""),
        "approach": params.get("approach", ""),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }
    os.makedirs(os.path.join(boros_dir, "session"), exist_ok=True)
    with open(os.path.join(boros_dir, "session", "evolution_target.json"), "w") as f:
        json.dump(target, f, indent=2)
    return {"status": "ok", "target": target}
