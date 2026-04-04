
import os, json, datetime
def loop_start(params: dict, kernel=None) -> dict:
    boros_dir = str(kernel.boros_root) if kernel else "boros"

    # Read current cycle number
    cycle_file = os.path.join(boros_dir, "session", "current_cycle.json")
    cycle_num = 1
    if os.path.exists(cycle_file):
        with open(cycle_file) as f:
            cycle_num = json.load(f).get("cycle", 0) + 1

    # Keep existing mode if present
    session_state_file = os.path.join(boros_dir, "session", "loop_state.json")
    current_mode = "evolution"
    if os.path.exists(session_state_file):
        try:
            with open(session_state_file) as sf:
                current_mode = json.load(sf).get("mode", "evolution")
        except: pass

    state = {
        "cycle": cycle_num,
        "stage": "REFLECT",
        "mode": current_mode,
        "cycle_started_at": datetime.datetime.utcnow().isoformat() + "Z",
        "total_cycles_completed": cycle_num - 1
    }

    # Write to session
    os.makedirs(os.path.join(boros_dir, "session"), exist_ok=True)
    with open(session_state_file, "w") as f:
        json.dump(state, f, indent=2)
    with open(cycle_file, "w") as f:
        json.dump({"cycle": cycle_num}, f)

    # Fire context load
    if kernel and "context_load" in kernel.registry:
        kernel.registry["context_load"]({}, kernel)

    return {"status": "ok", "state": state}
