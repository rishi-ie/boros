
import os, json, datetime

def loop_start(params: dict, kernel=None) -> dict:
    boros_dir = str(kernel.boros_root) if kernel else os.getcwd()

    session_dir = os.path.join(boros_dir, "session")
    os.makedirs(session_dir, exist_ok=True)
    session_state_file = os.path.join(session_dir, "loop_state.json")
    cycle_file = os.path.join(session_dir, "current_cycle.json")

    # Crash-safe recovery: detect incomplete previous cycle and roll back
    crashed = False
    crash_details = {}
    if os.path.exists(session_state_file):
        try:
            with open(session_state_file) as sf:
                prev_state = json.load(sf)
            prev_stage = prev_state.get("stage")
            # If stage is not None and not END, the previous cycle never completed
            if prev_stage and prev_stage not in (None, "END"):
                crashed = True
                crash_details["crashed_stage"] = prev_stage
                crash_details["crashed_cycle"] = prev_state.get("cycle", "unknown")
                print(f"[loop_start] WARNING: Previous cycle crashed in stage '{prev_stage}'. Running aggressive recovery.")

                # Roll back to the last snapshot if one was recorded
                target_file = os.path.join(session_dir, "evolution_target.json")
                if os.path.exists(target_file):
                    try:
                        with open(target_file) as f:
                            tgt = json.load(f)
                        target = tgt.get("target") or tgt.get("target_skill")
                        snapshot_id = tgt.get("snapshot_id")
                        if target and snapshot_id and kernel and "forge_rollback" in kernel.registry:
                            result = kernel.registry["forge_rollback"](
                                {"target": target, "snapshot_id": snapshot_id}, kernel
                            )
                            crash_details["rollback_target"] = target
                            crash_details["rollback_snapshot"] = snapshot_id
                            crash_details["rollback_result"] = result.get("status", "unknown")
                            print(f"[CRASH RECOVERY] Rolled back {target} to {snapshot_id}: {result.get('status')}")
                    except (json.JSONDecodeError, OSError) as e:
                        crash_details["rollback_error"] = str(e)
                        print(f"[CRASH RECOVERY] Rollback failed: {e}")

                # Clean up stale session files
                stale_files = ["hypothesis.json", "evolution_target.json", "review_feedback.json",
                               "pending_eval.json"]
                for stale in stale_files:
                    path = os.path.join(session_dir, stale)
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except OSError:
                            pass

                # Also clean proposals directory
                proposals_dir = os.path.join(session_dir, "proposals")
                if os.path.isdir(proposals_dir):
                    for item in os.listdir(proposals_dir):
                        try:
                            os.remove(os.path.join(proposals_dir, item))
                        except OSError:
                            pass

                # Record the crash for learning
                try:
                    crash_record = {
                        "type": "crash_recovery",
                        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                        "crashed_stage": prev_stage,
                        "crashed_cycle": prev_state.get("cycle"),
                        "snapshot_rolled_back": crash_details.get("rollback_snapshot"),
                        "target_skill": crash_details.get("rollback_target"),
                    }
                    records_dir = os.path.join(boros_dir, "memory", "evolution_records")
                    os.makedirs(records_dir, exist_ok=True)
                    crash_filename = f"crash-{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(os.path.join(records_dir, crash_filename), "w") as f:
                        json.dump(crash_record, f, indent=2)
                except Exception as e:
                    print(f"[CRASH RECOVERY] Failed to write crash record: {e}")

        except (json.JSONDecodeError, OSError):
            pass

    cycle_num = 1
    if os.path.exists(cycle_file):
        try:
            with open(cycle_file) as f:
                cycle_num = json.load(f).get("cycle", 0) + 1
        except (json.JSONDecodeError, OSError):
            pass

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
        result["crash_details"] = crash_details
    return result
