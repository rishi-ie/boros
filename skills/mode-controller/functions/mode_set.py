
import os, json
def mode_set(params: dict, kernel=None) -> dict:
    boros_dir = str(kernel.boros_root) if kernel else __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))))
    mode = params.get("mode", "evolution")
    state_file = os.path.join(boros_dir, "session", "loop_state.json")
    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    state = {}
    if os.path.exists(state_file):
        with open(state_file) as f:
            state = json.load(f)
    state["mode"] = mode
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)
    return {"status": "ok", "mode": mode}
