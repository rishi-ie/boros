
import os, json, uuid, datetime
from .validate import validate_skill_syntax
def evolve_propose(params: dict, kernel=None) -> dict:
    """Create a formal evolution proposal. Stores proposal artifact in session."""
    
    # First, validate the skill's/file's syntax
    target_to_validate = params.get("target", params.get("skill_name"))
    if target_to_validate and kernel:
        if 'forge_validate' in kernel.registry:
            validation_result = kernel.registry['forge_validate'](
                {"target": target_to_validate}, kernel
            )
            if validation_result.get("status") != "ok":
                return {
                    "status": "error",
                    "message": "Syntax validation failed. Proposal aborted.",
                    "details": validation_result.get("errors", [])
                }
        else:
            # forge_validate not loaded yet — skip validation gracefully
            pass
            
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    prop_id = f"prop-{uuid.uuid4().hex[:8]}"

    proposal = {
        "id": prop_id,
        "target": target_to_validate,
        "snapshot_id": params.get("snapshot_id", ""),
        "description": params.get("description", ""),
        "target_file": params.get("target_file", ""),
        "diff_summary": params.get("diff_summary", ""),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "status": "pending_review"
    }

    # Read hypothesis context
    hyp_file = os.path.join(boros_dir, "session", "hypothesis.json")
    if os.path.exists(hyp_file):
        with open(hyp_file) as f:
            proposal["hypothesis"] = json.load(f)

    # Save proposal
    proposals_dir = os.path.join(boros_dir, "session", "proposals")
    os.makedirs(proposals_dir, exist_ok=True)
    with open(os.path.join(proposals_dir, f"{prop_id}.json"), "w") as f:
        json.dump(proposal, f, indent=2)

    return {"status": "ok", "proposal_id": prop_id, "proposal": proposal}
