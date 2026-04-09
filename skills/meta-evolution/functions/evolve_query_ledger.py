
import os, sys

def evolve_query_ledger(params: dict, kernel=None) -> dict:
    """Query the evolution ledger — your institutional memory of every change and its outcome.

    Use this during REFLECT to understand what worked, what failed, and what's blocked.

    Parameters:
        mode (str): One of:
            "file_history"   — All attempts on a specific file (requires target_file)
            "skill_stats"    — Success/regression rates for a skill (requires target_skill)
            "regressions"    — All recent regressions across all skills
            "improvements"   — All recent improvements across all skills
            "recent"         — Last N ledger entries regardless of outcome
        target_file (str):  Path to a specific file (for file_history mode)
        target_skill (str): Skill name (for skill_stats mode)
        limit (int):        Max entries to return (default 20)

    Returns:
        Structured history with cycle, approach, outcome, score_before, score_after, delta.
    """
    boros_dir = str(kernel.boros_root) if kernel else os.getcwd()

    # Import ledger from internal module
    ledger_path = os.path.join(boros_dir, "skills", "meta-evolution", "functions", "_internal")
    if ledger_path not in sys.path:
        sys.path.insert(0, ledger_path)

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "evolution_ledger",
            os.path.join(ledger_path, "evolution_ledger.py")
        )
        ledger_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ledger_mod)
    except Exception as e:
        return {"status": "error", "message": f"Could not load ledger: {e}"}

    mode = params.get("mode", "recent")
    target_file = params.get("target_file", "")
    target_skill = params.get("target_skill", "")
    limit = params.get("limit", 20)

    if mode == "file_history":
        if not target_file:
            return {"status": "error", "message": "file_history mode requires target_file parameter"}
        entries = ledger_mod.get_file_history(boros_dir, target_file)
        summary = _summarize_entries(entries)
        return {
            "status": "ok",
            "mode": mode,
            "target_file": target_file,
            "entries": entries[-limit:],
            "summary": summary
        }

    elif mode == "skill_stats":
        if not target_skill:
            return {"status": "error", "message": "skill_stats mode requires target_skill parameter"}
        stats = ledger_mod.get_skill_stats(boros_dir, target_skill)
        recent = ledger_mod.query_ledger(boros_dir, target_skill=target_skill, limit=limit)
        return {
            "status": "ok",
            "mode": mode,
            "target_skill": target_skill,
            "stats": stats,
            "recent_attempts": recent
        }

    elif mode == "regressions":
        entries = ledger_mod.get_regressions(boros_dir, limit=limit)
        return {
            "status": "ok",
            "mode": mode,
            "regressions": entries,
            "count": len(entries),
            "advice": "These are the approaches that made things WORSE. Do not repeat them."
        }

    elif mode == "improvements":
        entries = ledger_mod.query_ledger(boros_dir, outcome="improved", limit=limit)
        return {
            "status": "ok",
            "mode": mode,
            "improvements": entries,
            "count": len(entries),
            "advice": "These are the approaches that worked. Study the pattern."
        }

    else:  # "recent"
        entries = ledger_mod.query_ledger(boros_dir, limit=limit)
        return {
            "status": "ok",
            "mode": mode,
            "entries": entries,
            "count": len(entries)
        }


def _summarize_entries(entries: list) -> dict:
    """Produce a quick summary of a list of ledger entries."""
    if not entries:
        return {"attempts": 0}
    outcomes = [e.get("outcome", "unknown") for e in entries]
    return {
        "attempts": len(entries),
        "improved": outcomes.count("improved"),
        "regressed": outcomes.count("regressed"),
        "neutral": outcomes.count("neutral"),
        "last_outcome": outcomes[-1] if outcomes else None,
        "last_approach": entries[-1].get("approach", "")[:120] if entries else None,
        "last_delta": entries[-1].get("delta") if entries else None,
    }
