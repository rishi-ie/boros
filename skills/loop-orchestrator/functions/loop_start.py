
import os, json, datetime
def loop_start(params: dict, kernel=None) -> dict:
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    
    # Read current cycle number
    cycle_file = os.path.join(boros_dir, "session", "current_cycle.json")
    cycle_num = 1
    if os.path.exists(cycle_file):
        with open(cycle_file) as f:
            cycle_num = json.load(f).get("cycle", 0) + 1

    state = {
        "cycle": cycle_num,
        "stage": "REFLECT",
        "mode": "evolution",
        "cycle_started_at": datetime.datetime.utcnow().isoformat() + "Z",
        "total_cycles_completed": cycle_num - 1
    }

    # Write loop state
    state_dir = os.path.join(boros_dir, "skills", "loop-orchestrator", "state")
    os.makedirs(state_dir, exist_ok=True)
    with open(os.path.join(state_dir, "loop_state.json"), "w") as f:
        json.dump(state, f, indent=2)

    # Also write to session
    os.makedirs(os.path.join(boros_dir, "session"), exist_ok=True)
    with open(os.path.join(boros_dir, "session", "loop_state.json"), "w") as f:
        json.dump(state, f, indent=2)
    with open(cycle_file, "w") as f:
        json.dump({"cycle": cycle_num}, f)

    # Fire context load
    if kernel and "context_load" in kernel.registry:
        kernel.registry["context_load"]({}, kernel)

    return {"status": "ok", "state": state}
