
import os, json
def context_load(params: dict, kernel=None) -> dict:
    """Load fresh context at cycle start: identity, scores, hypothesis, recent experiences."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    manifest = {}

    # Load recent evolution records (last 5)
    evolution_records_dir = os.path.join(boros_dir, "memory", "evolution_records")
    manifest["evolution_records"] = []
    if os.path.exists(evolution_records_dir):
        record_files = sorted([f for f in os.listdir(evolution_records_dir) if f.endswith(".json")], key=lambda x: os.path.getmtime(os.path.join(evolution_records_dir, x)))
        for record_file in record_files[-5:]:
            try:
                with open(os.path.join(evolution_records_dir, record_file)) as f:
                    manifest["evolution_records"].append(json.load(f))
            except json.JSONDecodeError as e:
                print(f"Warning: Could not parse evolution record {record_file}: {e}")

    # Load recent experiences (last 5)
    experiences_file = os.path.join(boros_dir, "memory", "experiences", "experiences.jsonl")
    manifest["recent_experiences"] = []
    if os.path.exists(experiences_file):
        with open(experiences_file) as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        for l in lines[-5:]:
            try:
                manifest["recent_experiences"].append(json.loads(l))
            except json.JSONDecodeError as e:
                print(f"Warning: Could not parse experience line: {l} - {e}")

    # Load recent scores
    score_file = os.path.join(boros_dir, "memory", "score_history.jsonl")
    if os.path.exists(score_file):
        with open(score_file) as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        manifest["recent_scores"] = [json.loads(l) for l in lines[-5:]] if lines else []

    # Load hypothesis if present
    hyp_file = os.path.join(boros_dir, "session", "hypothesis.json")
    if os.path.exists(hyp_file):
        with open(hyp_file) as f:
            manifest["hypothesis"] = json.load(f)

    # Load high-water marks
    hw_file = os.path.join(boros_dir, "skills", "eval-bridge", "state", "high_water_marks.json")
    if os.path.exists(hw_file):
        with open(hw_file) as f:
            manifest["high_water_marks"] = json.load(f)

    # Save context manifest
    os.makedirs(os.path.join(boros_dir, "session"), exist_ok=True)
    with open(os.path.join(boros_dir, "session", "context_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    return {"status": "ok", "loaded": True, "manifest_keys": list(manifest.keys()), "content": manifest}
