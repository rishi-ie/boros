
import os, json, datetime
def loop_advance_stage(params: dict, kernel=None) -> dict:
    boros_dir = str(kernel.boros_root) if kernel else __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))))

    state_file = os.path.join(boros_dir, "session", "loop_state.json")
    if not os.path.exists(state_file):
        return {"status": "error", "message": "Loop not started. Call loop_start first."}

    with open(state_file) as f:
        state = json.load(f)

    current = params.get("current_stage", state.get("stage", "REFLECT"))
    stages = ["REFLECT", "EVOLVE", "EVAL", "END"]
    idx = stages.index(current) if current in stages else 0
    next_stage = stages[idx + 1] if idx + 1 < len(stages) else "END"

    # Hard gate: REFLECT → EVOLVE requires a written hypothesis
    if current == "REFLECT" and next_stage == "EVOLVE":
        hyp_file = os.path.join(boros_dir, "session", "hypothesis.json")
        if not os.path.exists(hyp_file):
            return {
                "status": "error",
                "message": "Cannot advance to EVOLVE without a hypothesis. Call reflection_write_hypothesis first."
            }

    state["stage"] = next_stage
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)

    return {"status": "ok", "previous_stage": current, "next_stage": next_stage, "state": state}
