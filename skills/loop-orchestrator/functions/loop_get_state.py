
import os, json
def loop_get_state(params: dict, kernel=None) -> dict:
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    state_file = os.path.join(boros_dir, "session", "loop_state.json")
    if os.path.exists(state_file):
        with open(state_file) as f:
            state = json.load(f)
        return {"status": "ok", "state": state}
    return {"status": "ok", "state": None, "message": "Loop not started."}
