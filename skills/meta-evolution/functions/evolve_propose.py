
import os, json, uuid, datetime
from .validate import validate_skill_syntax

def evolve_propose(params: dict, kernel=None) -> dict:
    """Create a formal evolution proposal. Stores proposal artifact in session.
    
    FIX-11: Requires a hypothesis before allowing proposals.
    FIX-06: Checks anti-brute-force before allowing modifications.
    """
    boros_dir = str(kernel.boros_root) if kernel else "boros"

    # ── FIX-11: Enforce hypothesis requirement ───────────────────
    hyp_file = os.path.join(boros_dir, "session", "hypothesis.json")
    if not os.path.exists(hyp_file):
        return {
            "status": "error",
            "message": "Cannot create proposal without a hypothesis. Call reflection_write_hypothesis first."
        }

    try:
        with open(hyp_file) as f:
            hypothesis = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return {"status": "error", "message": f"Failed to read hypothesis: {e}"}

    if not hypothesis.get("rationale") or not hypothesis.get("expected_improvement"):
        return {
            "status": "error",
            "message": "Hypothesis must have 'rationale' and 'expected_improvement' fields."
        }

    # ── FIX-06: Anti-brute-force check ───────────────────────────
    proposal_target_file = params.get("target_file", "")
    if proposal_target_file:
        try:
            import importlib.util
            _lp = os.path.join(boros_dir, "skills", "meta-evolution", "functions", "_internal", "evolution_ledger.py")
            _sp = importlib.util.spec_from_file_location("evolution_ledger", _lp)
            ledger = importlib.util.module_from_spec(_sp)
            _sp.loader.exec_module(ledger)
            block = ledger.check_brute_force(boros_dir, proposal_target_file)
            if block:
                return block
        except Exception:
            pass  # Ledger not available yet — don't block on first run

    # ── Validate syntax before proposing ─────────────────────────
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
            
    prop_id = f"prop-{uuid.uuid4().hex[:8]}"

    proposal = {
        "id": prop_id,
        "target": target_to_validate,
        "snapshot_id": params.get("snapshot_id", ""),
        "description": params.get("description", ""),
        "target_file": proposal_target_file,
        "diff_summary": params.get("diff_summary", ""),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "status": "pending_review",
        "hypothesis": hypothesis,  # Always attach hypothesis now
    }

    # Save proposal
    proposals_dir = os.path.join(boros_dir, "session", "proposals")
    os.makedirs(proposals_dir, exist_ok=True)
    with open(os.path.join(proposals_dir, f"{prop_id}.json"), "w") as f:
        json.dump(proposal, f, indent=2)

    return {"status": "ok", "proposal_id": prop_id, "proposal": proposal}

