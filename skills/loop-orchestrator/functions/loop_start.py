
import os, json, datetime

def loop_start(params: dict, kernel=None) -> dict:
    boros_dir = str(kernel.boros_root) if kernel else os.getcwd()

    session_dir = os.path.join(boros_dir, "session")
    os.makedirs(session_dir, exist_ok=True)
    session_state_file = os.path.join(session_dir, "loop_state.json")
    cycle_file = os.path.join(session_dir, "current_cycle.json")

    # ── Crash recovery: detect and clean up unfinished previous cycle ──
    crashed = False
    if os.path.exists(session_state_file):
        try:
            with open(session_state_file) as sf:
                prev_state = json.load(sf)
            prev_stage = prev_state.get("stage")
            # If stage is not None and not END, the previous cycle never completed
            if prev_stage and prev_stage not in (None, "END"):
                crashed = True
                print(f"[loop_start] WARNING: Previous cycle crashed in stage '{prev_stage}'. Cleaning up and starting fresh.")
                # Attempt rollback if a snapshot was active
                if kernel and "forge_rollback" in kernel.registry:
                    target_file = os.path.join(session_dir, "evolution_target.json")
                    if os.path.exists(target_file):
                        try:
                            with open(target_file) as f:
                                tgt = json.load(f)
                            target = tgt.get("target")
                            snapshot_id = tgt.get("snapshot_id")
                            if target and snapshot_id:
                                kernel.registry["forge_rollback"](
                                    {"target": target, "snapshot_id": snapshot_id}, kernel
                                )
                                print(f"[loop_start] Auto-rollback executed for crashed cycle: {target}")
                        except (json.JSONDecodeError, OSError):
                            pass
        except (json.JSONDecodeError, OSError):
            pass

    # ── Read current cycle number ──────────────────────────────
    cycle_num = 1
    if os.path.exists(cycle_file):
        try:
            with open(cycle_file) as f:
                cycle_num = json.load(f).get("cycle", 0) + 1
        except (json.JSONDecodeError, OSError):
            pass

    # ── Keep existing mode ─────────────────────────────────────
    current_mode = "evolution"
    if os.path.exists(session_state_file):
        try:
            with open(session_state_file) as sf:
                current_mode = json.load(sf).get("mode", "evolution")
        except (json.JSONDecodeError, OSError):
            pass

    state = {
        "cycle": cycle_num,
        "stage": "REFLECT",
        "mode": current_mode,
        "cycle_started_at": datetime.datetime.utcnow().isoformat() + "Z",
        "total_cycles_completed": cycle_num - 1
    }

    with open(session_state_file, "w") as f:
        json.dump(state, f, indent=2)
    with open(cycle_file, "w") as f:
        json.dump({"cycle": cycle_num}, f)

    if kernel and "context_load" in kernel.registry:
        kernel.registry["context_load"]({}, kernel)

    result = {"status": "ok", "state": state}
    if crashed:
        result["recovered_from_crash"] = True
    return result
