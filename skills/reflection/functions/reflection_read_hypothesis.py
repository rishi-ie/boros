
import os, json
def reflection_read_hypothesis(params: dict, kernel=None) -> dict:
    """Read the current cycle's hypothesis from session."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    hyp_file = os.path.join(boros_dir, "session", "hypothesis.json")
    if os.path.exists(hyp_file):
        with open(hyp_file, "r") as f:
            hyp = json.load(f)
        return {"status": "ok", "hypothesis": hyp}
    return {"status": "ok", "hypothesis": None, "message": "No active hypothesis for this cycle."}
