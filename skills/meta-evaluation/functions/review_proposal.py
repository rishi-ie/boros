
import os, json, datetime
def review_proposal(params: dict, kernel=None) -> dict:
    """Submit a proposal to the Meta-Evaluation Review Board (secondary LLM).
    If meta_eval_llm is available, calls it for independent review.
    Falls back to rule-based review if no LLM is available."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"

    proposal_id = params.get("proposal_id", "unknown")
    diff = params.get("diff", "")
    description = params.get("description", "")
    target_file = params.get("target_file", "")

    # Try LLM-based review
    if kernel and kernel.meta_eval_llm:
        try:
            review_prompt = (
                f"You are the Boros Meta-Evaluation Review Board. Your job is to review "
                f"code changes proposed by the evolution engine and decide: apply, reject, or modify.\n\n"
                f"## Proposal: {proposal_id}\n"
                f"**Description:** {description}\n"
                f"**Target File:** {target_file}\n\n"
                f"## Code Diff:\n```\n{diff}\n```\n\n"
                f"Evaluate for:\n"
                f"1. Correctness: Will this code run without errors?\n"
                f"2. Improvement: Does it genuinely improve the function?\n"
                f"3. Safety: Could it break other parts of the system?\n"
                f"4. Python syntax: Is it valid Python?\n"
                f"5. Algorithmic Depth: Does this change modify control flow, algorithms, or structural capability?\n\n"
                f"CRITICAL REJECTION CRITERIA:\n"
                f"You MUST return 'reject' if the proposal ONLY changes string phrasing, comment text, prompts, or docstrings without adding meaningful programmatic execution logic. Cosmetic or trivial refactors MUST be rejected. Boros is trying to evolve its logic, not its writing style.\n\n"
                f"Respond with EXACTLY one JSON object:\n"
                f'{{"verdict": "apply"|"reject"|"modify", "reason": "...", "confidence": 0.0-1.0}}'
            )

            response = kernel.meta_eval_llm.complete(
                [{"role": "user", "content": review_prompt}],
                system="You are a strict code reviewer. Respond only with the requested JSON."
            )

            # Parse LLM response
            response_text = ""
            for block in response.get("content", []):
                if block.get("type") == "text":
                    response_text += block["text"]

            # Safely extract the outermost JSON object (handles nested braces)
            review = None
            start = response_text.find("{")
            if start != -1:
                for end in range(len(response_text), start, -1):
                    try:
                        review = json.loads(response_text[start:end])
                        break
                    except json.JSONDecodeError:
                        continue

            if review:
                verdict = review.get("verdict", "reject")
                reason = review.get("reason", "LLM review")
                confidence = review.get("confidence", 0.5)
            else:
                verdict = "reject"
                reason = f"LLM responded but no parseable JSON found. Rejecting for safety. Response: {response_text[:200]}"
                confidence = 0.2

        except Exception as e:
            verdict = "reject"
            reason = f"Meta-eval LLM call failed ({e}). Rejecting for safety — will retry next cycle."
            confidence = 0.1
    else:
        # Rule-based fallback
        verdict = "apply"
        reason = "No meta-eval LLM configured. Rule-based approval."
        confidence = 0.5
        if not diff or len(diff.strip()) < 10:
            verdict = "reject"
            reason = "Empty or trivial diff."
            confidence = 0.9

    review_record = {
        "proposal_id": proposal_id,
        "verdict": verdict,
        "reason": reason,
        "confidence": confidence,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "reviewer": "meta_eval_llm" if (kernel and kernel.meta_eval_llm) else "rule_based"
    }

    # Save review record
    reviews_dir = os.path.join(boros_dir, "memory", "evolution_records")
    os.makedirs(reviews_dir, exist_ok=True)
    with open(os.path.join(reviews_dir, f"review-{proposal_id}.json"), "w") as f:
        json.dump(review_record, f, indent=2)

    # On "modify": write structured feedback to session so LLM can act on it, then rollback
    # On "reject": rollback and stop — proposal is dead
    if verdict == "modify":
        try:
            os.makedirs(os.path.join(boros_dir, "session"), exist_ok=True)
            feedback = {
                "proposal_id": proposal_id,
                "verdict": "modify",
                "feedback": reason,
                "target_file": target_file,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }
            with open(os.path.join(boros_dir, "session", "review_feedback.json"), "w") as f:
                json.dump(feedback, f, indent=2)
        except Exception as e:
            reason += f" [feedback write failed: {e}]"
        # Still rollback the file changes since they weren't approved
        _do_rollback(boros_dir, proposal_id, kernel, reason)

    elif verdict == "reject":
        _do_rollback(boros_dir, proposal_id, kernel, reason)

    return {"status": "ok", "verdict": verdict, "reason": reason, "confidence": confidence}


def _do_rollback(boros_dir, proposal_id, kernel, reason):
    """Restore skill files from snapshot after a non-apply verdict."""
    if not kernel:
        return
    try:
        prop_file = os.path.join(boros_dir, "session", "proposals", f"{proposal_id}.json")
        if not os.path.exists(prop_file):
            # Also try evolution_target for snapshot_id
            target_file = os.path.join(boros_dir, "session", "evolution_target.json")
            if os.path.exists(target_file):
                with open(target_file) as f:
                    target_data = json.load(f)
                snapshot_id = target_data.get("snapshot_id")
                skill_name  = target_data.get("target_skill")
                if snapshot_id and skill_name and "forge_rollback" in kernel.registry:
                    kernel.registry["forge_rollback"]({"target": skill_name, "snapshot_id": snapshot_id}, kernel)
            return
        with open(prop_file) as f:
            proposal = json.load(f)
        target      = proposal.get("target", proposal.get("skill_name"))
        snapshot_id = proposal.get("snapshot_id")
        if target and snapshot_id and "forge_rollback" in kernel.registry:
            kernel.registry["forge_rollback"]({"target": target, "snapshot_id": snapshot_id}, kernel)
    except Exception as rollback_e:
        print(f"[review_proposal] rollback failed: {rollback_e}")
