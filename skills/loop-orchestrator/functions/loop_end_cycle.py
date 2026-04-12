
import os, json, datetime, uuid


def loop_end_cycle(params: dict, kernel=None) -> dict:
    """End the current evolution cycle. Records outcome to the evolution ledger,
    updates high-water marks, writes KG triples, and cleans session state."""
    boros_dir = str(kernel.boros_root) if kernel else __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))))

    state_file = os.path.join(boros_dir, "session", "loop_state.json")
    if os.path.exists(state_file):
        with open(state_file) as f:
            state = json.load(f)
        cycle = state.get("cycle", 1)
        state["stage"] = None
        state["cycle_ended_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
    else:
        cycle = 0

    hyp_file = os.path.join(boros_dir, "session", "hypothesis.json")
    hypothesis = {}
    if os.path.exists(hyp_file):
        try:
            with open(hyp_file) as f:
                hypothesis = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    target_data = {}
    target_file_path = os.path.join(boros_dir, "session", "evolution_target.json")
    if os.path.exists(target_file_path):
        try:
            with open(target_file_path) as f:
                target_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    target_skill = target_data.get("target_skill", hypothesis.get("target_skill", ""))
    snapshot_id = target_data.get("snapshot_id", "")
    target_file = target_data.get("target_file", "")

    # Compute score delta
    score_hist_path = os.path.join(boros_dir, "memory", "score_history.jsonl")
    score_before, score_after, outcome = {}, {}, "unknown"
    delta = None
    target_cat = target_skill  # category usually matches skill name

    if os.path.exists(score_hist_path):
        try:
            with open(score_hist_path) as f:
                lines = [ln for ln in f if ln.strip()]
            entries = [json.loads(l) for l in lines]
            scored = [e for e in entries if e.get("scores")]
            if len(scored) >= 2:
                score_before = scored[-2].get("scores", {})
                score_after = scored[-1].get("scores", {})
            elif len(scored) == 1:
                score_after = scored[-1].get("scores", {})
        except Exception:
            pass

    # Determine outcome for the target category
    before_val = None
    after_val = None
    if target_cat and target_cat in score_after:
        after_val = score_after[target_cat]
        before_val = score_before.get(target_cat)

    if before_val is not None and after_val is not None:
        delta = round(after_val - before_val, 4)
        if delta > 0.02:
            outcome = "improved"
        elif delta < -0.02:
            outcome = "regressed"
        else:
            outcome = "neutral"
    elif after_val is not None:
        outcome = "baseline"

    # Read auto-rollback status written by eval_check_regression
    auto_rollback = None
    records_dir = os.path.join(boros_dir, "memory", "evolution_records")
    rollback_file = os.path.join(records_dir, f"rollback-cycle{cycle}.json")
    if os.path.exists(rollback_file):
        try:
            with open(rollback_file) as f:
                rb_data = json.load(f)
            auto_rollback = {
                "snapshot_id": rb_data.get("snapshot_id"),
                "target_skill": rb_data.get("skill_name"),
                "result": "ok"
            }
            outcome = "regressed"
        except Exception as e:
            print(f"[loop_end_cycle] WARNING: Failed to read rollback data: {e}")

    # Write evolution ledger entry
    # Read proposal info if available
    proposal_id = ""
    approach = hypothesis.get("rationale", params.get("description", ""))
    review_verdict = ""
    proposals_dir = os.path.join(boros_dir, "session", "proposals")
    if os.path.isdir(proposals_dir):
        for fname in os.listdir(proposals_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(proposals_dir, fname)) as f:
                        prop = json.load(f)
                    proposal_id = prop.get("id", "")
                    if not approach:
                        approach = prop.get("description", "")
                    if not target_file:
                        target_file = prop.get("target_file", "")
                    break  # Use first proposal found
                except Exception:
                    pass

    # Check for review verdict
    review_file = os.path.join(boros_dir, "memory", "evolution_records", f"review-{proposal_id}.json")
    if os.path.exists(review_file):
        try:
            with open(review_file) as f:
                review_data = json.load(f)
            review_verdict = review_data.get("verdict", "")
        except Exception:
            pass

    try:
        # importlib.util is required because the hyphen in "meta-evolution" breaks importlib.import_module
        import importlib.util
        _ledger_path = os.path.join(boros_dir, "skills", "meta-evolution", "functions", "_internal", "evolution_ledger.py")
        _spec = importlib.util.spec_from_file_location("evolution_ledger", _ledger_path)
        ledger_module = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(ledger_module)
        ledger_entry = {
            "cycle": cycle,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "target_skill": target_skill,
            "target_file": target_file,
            "category": target_cat,
            "approach": approach[:500] if approach else "",
            "proposal_id": proposal_id,
            "snapshot_id": snapshot_id,
            "score_before": score_before,
            "score_after": score_after,
            "delta": delta,
            "outcome": outcome,
            "review_verdict": review_verdict,
            "hypothesis_rationale": hypothesis.get("rationale", "")[:500],
            "auto_rollback": auto_rollback,
        }
        ledger_module.record_attempt(boros_dir, ledger_entry)
    except Exception as e:
        print(f"[loop_end_cycle] WARNING: Failed to write evolution ledger: {e}")

    # Write knowledge graph triples
    if kernel and "memory_kg_write" in kernel.registry:
        try:
            kg = kernel.registry["memory_kg_write"]

            # Record scores
            for cat, score in score_after.items():
                kg({"subject": cat, "predicate": "has_score",
                    "object": str(score), "cycle": cycle}, kernel)

            # Record what was modified
            if target_skill:
                kg({"subject": target_skill, "predicate": "was_modified",
                    "object": approach[:200] if approach else "unknown", "cycle": cycle}, kernel)

            # Record causal link
            if target_skill and target_cat and delta is not None:
                kg({"subject": target_skill, "predicate": "caused_delta_in",
                    "object": f"{target_cat}:{delta:+.4f}", "cycle": cycle,
                    "metadata": {"outcome": outcome}}, kernel)
        except Exception as e:
            print(f"[loop_end_cycle] WARNING: KG write failed: {e}")

    # Archive hypothesis with outcome data
    hypothesis_archived = False
    if hypothesis:
        try:
            archive_entry = {
                "id": hypothesis.get("id", f"hyp-{uuid.uuid4().hex[:8]}"),
                "cycle": cycle,
                "target_skill": target_skill,
                "rationale": hypothesis.get("rationale", ""),
                "expected_improvement": hypothesis.get("expected_improvement", ""),
                "actual_outcome": outcome,
                "score_delta": delta,
                "score_before": score_before,
                "score_after": score_after,
                "auto_rollback": auto_rollback,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }
            records_dir = os.path.join(boros_dir, "memory", "evolution_records")
            os.makedirs(records_dir, exist_ok=True)
            archive_path = os.path.join(records_dir, f"hyp-cycle{cycle}.json")
            with open(archive_path, "w") as f:
                json.dump(archive_entry, f, indent=2)
            hypothesis_archived = True
        except Exception as e:
            print(f"[loop_end_cycle] WARNING: hypothesis archival failed: {e}")

    # Update high-water marks
    hw_updated = {}
    if score_after and kernel and "eval_update_high_water" in kernel.registry:
        try:
            result = kernel.registry["eval_update_high_water"]({"scores": score_after}, kernel)
            hw_updated = result.get("updated_categories", {})
        except Exception as e:
            print(f"[loop_end_cycle] WARNING: high-water mark update failed: {e}")

    # Check for milestone advancement
    if kernel and "eval_check_milestone" in kernel.registry:
        try:
            milestone_result = kernel.registry["eval_check_milestone"]({}, kernel)
            if milestone_result.get("advanced"):
                print(f"[loop_end_cycle] Milestones advanced: {milestone_result['advanced']}")
        except Exception as e:
            print(f"[loop_end_cycle] WARNING: milestone check failed: {e}")

    # Record gene if this cycle improved scores
    if outcome == "improved" and kernel and "civ_record_gene" in kernel.registry:
        try:
            # Read diff content from proposal if available
            proposal_diff = ""
            proposals_dir_path = os.path.join(boros_dir, "session", "proposals")
            if os.path.isdir(proposals_dir_path):
                for fname in os.listdir(proposals_dir_path):
                    if fname.endswith(".json"):
                        try:
                            with open(os.path.join(proposals_dir_path, fname)) as f:
                                prop_data = json.load(f)
                            proposal_diff = prop_data.get("diff_content", "")
                            break
                        except Exception:
                            pass

            kernel.registry["civ_record_gene"]({
                "cycle": cycle,
                "target_skill": target_skill,
                "target_file": target_file,
                "approach": approach,
                "diff": proposal_diff,
                "score_delta": delta,
                "score_before": score_before,
                "score_after": score_after,
                "proposal_id": proposal_id,
                "review_verdict": review_verdict,
            }, kernel)
        except Exception as e:
            print(f"[loop_end_cycle] WARNING: gene recording failed: {e}")

    # Clean up session artifacts
    session_dir = os.path.join(boros_dir, "session")
    keep = {"loop_state.json", "current_cycle.json"}
    if os.path.isdir(session_dir):
        for item in os.listdir(session_dir):
            item_path = os.path.join(session_dir, item)
            if item not in keep and not os.path.isdir(item_path):
                try:
                    os.remove(item_path)
                except OSError:
                    pass
        # Clean proposals directory
        proposals_path = os.path.join(session_dir, "proposals")
        if os.path.isdir(proposals_path):
            for item in os.listdir(proposals_path):
                try:
                    os.remove(os.path.join(proposals_path, item))
                except OSError:
                    pass

    # Log cycle end
    log_file = os.path.join(boros_dir, "logs", "cycles.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, "a") as f:
        rollback_note = " [AUTO-ROLLED-BACK]" if auto_rollback else ""
        f.write(f"Cycle {cycle} ended at {datetime.datetime.utcnow().isoformat()}Z "
                f"| outcome={outcome} delta={delta}{rollback_note}\n")

    # Broadcast heartbeat
    if kernel and "civ_heartbeat" in kernel.registry:
        try:
            kernel.registry["civ_heartbeat"]({
                "cycle": cycle,
                "scores": score_after,
                "last_outcome": outcome,
                "last_delta": delta,
                "last_category": target_cat,
            }, kernel)
        except Exception as e:
            print(f"[loop_end_cycle] WARNING: heartbeat failed: {e}")

    return {
        "status": "ok",
        "cycle": cycle,
        "message": f"Cycle {cycle} complete.",
        "outcome": outcome,
        "delta": delta,
        "high_water_updated": hw_updated,
        "hypothesis_archived": hypothesis_archived,
        "auto_rollback": auto_rollback,
    }
