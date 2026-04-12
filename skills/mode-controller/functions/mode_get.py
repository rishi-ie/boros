
import os, json
def mode_get(params: dict, kernel=None) -> dict:
    boros_dir = str(kernel.boros_root) if kernel else __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))))
    state_file = os.path.join(boros_dir, "session", "loop_state.json")
    if os.path.exists(state_file):
        with open(state_file) as f:
            state = json.load(f)
        return {"status": "ok", "mode": state.get("mode", "evolution")}
    return {"status": "ok", "mode": "evolution"}
