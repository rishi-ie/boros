"""Evolution Ledger — The single source of truth for 'what worked?'

Every code change is linked to its score impact so Boros can learn from past cycles.

Ledger entry format:
{
    "cycle": 15,
    "timestamp": "2026-04-09T11:44:00Z",
    "target_skill": "memory",
    "target_file": "skills/memory/functions/memory_commit_archival.py",
    "category": "memory",
    "approach": "Added content validation requiring Context:/Action:/Outcome: phrases",
    "proposal_id": "prop-ebe3f690",
    "snapshot_id": "snap-1ccd4d98",
    "score_before": {"memory": 0.625},
    "score_after": {"memory": 0.709},
    "delta": 0.084,
    "outcome": "improved",         # improved | regressed | neutral | baseline
    "review_verdict": "apply",
    "hypothesis_rationale": "..."
}
"""

import os
import json

LEDGER_FILE = "memory/evolution_ledger.jsonl"


def record_attempt(boros_dir: str, entry: dict):
    """Append one evolution attempt to the ledger.
    
    This should be called at the end of every cycle by loop_end_cycle,
    regardless of outcome. Even crashes and baselines are valuable data.
    """
    path = os.path.join(boros_dir, LEDGER_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def query_ledger(boros_dir: str, target_file: str = None, target_skill: str = None,
                 outcome: str = None, limit: int = 20) -> list:
    """Query past evolution attempts with filters.
    
    Args:
        target_file: Filter by exact target file path.
        target_skill: Filter by skill name.
        outcome: Filter by outcome (improved/regressed/neutral/baseline).
        limit: Max entries to return (most recent first).
    """
    path = os.path.join(boros_dir, LEDGER_FILE)
    if not os.path.exists(path):
        return []

    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if target_file and entry.get("target_file") != target_file:
                continue
            if target_skill and entry.get("target_skill") != target_skill:
                continue
            if outcome and entry.get("outcome") != outcome:
                continue
            entries.append(entry)

    return entries[-limit:]


def get_file_history(boros_dir: str, target_file: str) -> list:
    """Get all evolution attempts that touched a specific file."""
    return query_ledger(boros_dir, target_file=target_file, limit=100)


def get_skill_stats(boros_dir: str, target_skill: str) -> dict:
    """Get aggregate statistics for a skill's evolution history.
    
    Returns dict with: attempts, improvements, regressions, neutral,
                       success_rate, last_outcome, last_approach
    """
    entries = query_ledger(boros_dir, target_skill=target_skill, limit=100)
    if not entries:
        return {"attempts": 0, "improvements": 0, "regressions": 0, "neutral": 0}

    stats = {"attempts": len(entries), "improvements": 0, "regressions": 0, "neutral": 0}
    for e in entries:
        outcome = e.get("outcome", "unknown")
        if outcome == "improved":
            stats["improvements"] += 1
        elif outcome == "regressed":
            stats["regressions"] += 1
        elif outcome == "neutral":
            stats["neutral"] += 1

    stats["success_rate"] = round(stats["improvements"] / max(stats["attempts"], 1), 3)
    stats["last_outcome"] = entries[-1].get("outcome")
    stats["last_approach"] = entries[-1].get("approach")
    return stats


def get_regressions(boros_dir: str, limit: int = 10) -> list:
    """Get recent regressions for system prompt warnings."""
    return query_ledger(boros_dir, outcome="regressed", limit=limit)


def check_brute_force(boros_dir: str, target_file: str) -> dict:
    """Check if this file was recently modified without improvement.

    Returns None if safe to proceed, or a block dict if brute-force detected.
    """
    history = get_file_history(boros_dir, target_file)
    if not history:
        return None  # No history, safe to proceed

    recent = history[-3:]  # Last 3 attempts on this file
    recent_failures = [e for e in recent if e.get("outcome") in ("regressed", "neutral")]

    if len(recent_failures) >= 2:
        return {
            "status": "blocked",
            "message": (
                f"Anti-brute-force: {target_file} was modified {len(recent_failures)} "
                f"times recently without improvement. Try a different file or approach."
            ),
            "recent_attempts": [
                {"cycle": e.get("cycle"), "approach": e.get("approach", "")[:80], "outcome": e.get("outcome")}
                for e in recent_failures
            ]
        }
    return None
