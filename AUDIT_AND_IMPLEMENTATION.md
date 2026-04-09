# BOROS AUDIT & IMPLEMENTATION PLAN

**Date:** 2026-04-09
**Scope:** Full codebase audit — every subsystem, every failure mode, every gap that prevents genuine self-evolution.

**Goal:** Make Boros a truly self-sovereign, self-evolving system with no practical limitations except the LLM itself. Every gap that can brick, stall, or mislead the system is documented and has a concrete fix.

---

## PART 1: AUDIT — WHAT'S BROKEN

### Severity Levels
- **S0 — SYSTEM BRICK**: Can permanently stop Boros from running
- **S1 — EVOLUTION KILLER**: Prevents meaningful self-improvement
- **S2 — QUALITY DRAIN**: Degrades evolution quality over time
- **S3 — PAPER CUT**: Minor issues that compound

---

### S0-01: No Path Protection on File Modification Tools
**Files:** `skills/tool-use/functions/tool_file_edit_diff.py`, `tool_file_write.py`, `tool_terminal.py`
**Problem:** Boros can modify `kernel.py`, `agent_loop.py`, `eval-generator/`, `config.json`, `manifest.json`, `.env` — any file on disk. The BANNED_SKILLS list in `evolve_orient.py` only filters *suggestions*, not actual file operations. `tool_terminal` runs `subprocess.Popen(command, shell=True)` with zero restrictions.
**Impact:** A single bad LLM decision can brick the entire system permanently. One `tool_file_write` to `kernel.py` with a syntax error = system never boots again.
**Evidence:** `tool_file_edit_diff.py` has no path validation. `tool_file_write.py` resolves paths relative to boros_root but doesn't check against any blacklist. `tool_terminal.py` executes arbitrary shell commands.

### S0-02: Crash During Cycle Leaves Bad Code Permanently
**Files:** `skills/loop-orchestrator/functions/loop_start.py`, `loop_end_cycle.py`
**Problem:** If a cycle crashes (timeout, API error, eval_id hallucination) between EVOLVE and COMMIT, the mutated code stays on disk but no outcome is recorded. Crash recovery in `loop_start` only calls `forge_rollback` if `evolution_target.json` has a `snapshot_id` — but that file may not exist or may have been deleted.
**Impact:** Observed in cycle 17: reformatter code (regression from 0.709 to 0.625) survived because the cycle crashed during `eval_read_scores` polling. No rollback fired. Cycle 18 started building on top of bad code.
**Evidence:** `loop_start.py` lines 12-40 — crash detection checks `stage != None` but if `loop_end_cycle` sets `stage = None` before archiving hypothesis (line 11), a crash during archival is invisible.

### S0-03: Skill `__init__.py` Corruption = Boot Failure
**File:** `kernel.py` lines 206-219
**Problem:** If Boros modifies a skill's `functions/__init__.py` to import a non-existent module, `_load_skills()` raises `RuntimeError` and the kernel never boots. There's no try/except per-skill — one broken skill kills everything.
**Impact:** Complete system halt requiring manual git restoration.

### S0-04: No Config/Manifest Integrity Validation
**Files:** `config.json`, `manifest.json`, `world_model.json`
**Problem:** These files are loaded at boot with no schema validation. Boros can corrupt them via `tool_file_edit_diff` or `tool_terminal`. Corrupted `manifest.json` = boot failure. Corrupted `world_model.json` = evolution targets disappear (we already saw this — the `categories` wrapper bug).
**Impact:** Silent misconfiguration or complete boot failure.

---

### S1-01: No Change-to-Outcome Correlation (THE BIGGEST GAP)
**Files:** `evolve_propose.py`, `evolve_apply.py`, `loop_end_cycle.py`, `evolve_history.py`
**Problem:** When Boros makes a code change (proposal), there is NO direct link stored between:
- What code was changed (proposal)
- What the score was before
- What the score was after
- Whether it improved, regressed, or was neutral

The data exists in *separate files* (`proposals/`, `hyp-cycleN.json`, `score_history.jsonl`) linked only by hypothesis ID. `evolve_history()` returns proposals but the LLM must manually cross-reference to find outcomes. There is no function that answers: "What happened when I last changed `memory_commit_archival.py`?"
**Impact:** Boros cannot programmatically learn from its mistakes. The anti-brute-force rule ("don't modify the same code twice if it didn't improve") is completely unenforceable because there's no data structure that maps file → change → outcome.
**Evidence:** `evolve_propose.py` stores `target_file`, `description`, `snapshot_id` but NOT `score_before`. `loop_end_cycle.py` computes outcome but stores it in a separate `hyp-cycleN.json` linked by hypothesis ID. No reverse lookup exists.

### S1-02: Anti-Brute-Force Rule Has Zero Enforcement
**Files:** All meta-evolution functions
**Problem:** BOROS.md line 46-52 says "If you modified a piece of Python code and it didn't improve the score, do not modify the same code again." No code tracks which files were modified, no code compares proposals against prior proposals on the same target, no code blocks repeated modifications.
**Impact:** Boros can loop endlessly on the same file with trivial variations. Observed in cycle 17: tried SKILL.md edit → rejected → tried reformatter → applied → regressed → no memory of this when cycle 18 started.

### S1-03: Automatic Regression Rollback Not Wired Into Cycle
**Files:** `eval_check_regression.py`, `loop_end_cycle.py`
**Problem:** `eval_check_regression` exists and works — it detects regressions and can call `evolve_rollback`. But it's a tool the LLM must *choose to call*. If the LLM doesn't call it (or the cycle crashes before COMMIT), regression goes undetected. `loop_end_cycle` calls `eval_check_milestone` but NOT `eval_check_regression`.
**Impact:** Bad code survives regressions when cycles crash or the LLM forgets to check.

### S1-04: Knowledge Graph Fully Implemented But Never Used
**Files:** `skills/memory/functions/memory_kg_write.py`, `memory_kg_query.py`
**Problem:** Complete temporal RDF-style knowledge graph with predicates (`has_score`, `was_modified`, `caused_delta_in`, `target_of`, `achieved_milestone`). Stores in SQLite. Supports history queries. Zero callers in entire codebase.
**Impact:** The single most powerful learning mechanism in the system is completely dark. Boros could query "show me everything that was_modified on the memory skill and what caused_delta_in the score" — but nobody writes these triples.

### S1-05: Review Board Auto-Approves When Meta-Eval LLM Is Down
**File:** `skills/meta-evaluation/functions/review_proposal.py` lines 73-75
**Problem:** If meta_eval_llm is not configured or fails, the fallback is:
```python
verdict = "apply"
reason = "No meta-eval LLM configured. Rule-based approval."
```
This means cosmetic changes, invalid changes, and even harmful changes get auto-approved when the review LLM is unavailable.
**Impact:** The only quality gate silently disappears.

### S1-06: eval_id Hallucination Causes 5-Minute Stalls
**Files:** `eval_request.py`, `eval_read_scores.py`
**Problem:** LLM invents eval IDs instead of using the one returned by `eval_request`. The `pending_eval.json` fallback helps but the current cycle must finish its 5-minute timeout before recovery.
**Impact:** Observed in cycles 14 and 17. Each hallucinated ID wastes 5 minutes and can cause the cycle to crash/timeout, leaving bad code in place (S0-02).
**Status:** Partially fixed with `pending_eval.json` fallback, but needs additional hardening.

### S1-07: Context Between Cycles Doesn't Surface Failures
**Files:** `skills/context-orchestration/functions/context_load.py`, `agent_loop.py` lines 116-148
**Problem:** `context_load()` loads the last 5 evolution records and 5 experiences without filtering by outcome. `agent_loop.py` shows the last 10 hypothesis outcomes in the system prompt — but in a flat list, not prioritizing regressions. If the last 10 cycles were all neutral, the one critical regression 11 cycles ago is invisible.
**Impact:** Boros repeats mistakes because it can't see what failed. The REFLECT stage starts with a clean slate every cycle.

### S1-08: Hypothesis Gate Not Enforced in Code
**File:** `evolve_propose.py` lines 38-42
**Problem:** `evolve_propose` reads `hypothesis.json` and attaches it if present — but doesn't error if it's missing. The LLM can propose changes without ever writing a hypothesis.
**Impact:** Evolution without theory = random mutation. No structured reasoning about what to try and why.

### S1-09: High-Water Marks Never Decay
**File:** `eval_update_high_water.py`
**Problem:** High-water marks only go up. A single lucky spike (0.85 on an easy task) becomes the permanent baseline. Every future score below 0.85 is treated as potential regression.
**Impact:** As score noise increases, high-water marks ratchet up to the maximum outlier. Eventually every eval triggers "regression" and the system gets stuck in permanent rollback loops.

### S1-10: Hot-Reload Can Fail Silently
**Files:** `kernel.py` lines 229-246, `evolve_apply.py` lines 48-53
**Problem:** `kernel.reload_skill()` uses `importlib.reload()` which doesn't reload transitive dependencies. If skill A imports a helper from skill B, reloading A doesn't pick up changes to B's helper. The reload result is not checked — `evolve_apply` reports "LIVE reloaded" even if reload failed.
**Impact:** Code changes appear to be live but old code paths are still active. Evals test old code, scores don't improve, Boros concludes the change was bad and rolls back a correct improvement.

---

### S2-01: Score History Unbounded Growth
**File:** `memory/score_history.jsonl`
**Problem:** Append-only, no rotation, no archival. `memory_page_in()` reads entire file into memory. After 10K evals → 1MB. After 1M evals → 100MB.
**Impact:** OOM or extreme slowdown during REFLECT.

### S2-02: Snapshot Directory Never Cleaned
**Files:** `snapshots/`, `config.json` lines 7-10
**Problem:** `config.json` defines `snapshot_retention` but no code implements the retention policy. Snapshots accumulate indefinitely.
**Impact:** Disk space leak.

### S2-03: Difficulty Scaling Not Used in Task Generation
**File:** `eval-generator/eval_generator.py` lines 135-177
**Problem:** Each milestone has a `difficulty` field (1-10) but task generation doesn't reference it. Level 3 difficulty tasks are generated the same way as level 8.
**Impact:** Milestone progression doesn't face harder tasks. Advancing from milestone 0 to 3 doesn't actually test progressively harder capabilities.

### S2-04: Cosmetic Change Detection Is LLM-Only
**File:** `review_proposal.py`
**Problem:** No AST-level comparison. No automated check that control flow actually changed. Entirely dependent on the meta_eval LLM's judgment.
**Impact:** LLM can be fooled by renaming variables, adding docstrings, reformatting code.

### S2-05: Experiences Stored With Empty Placeholders
**File:** `memory/experiences/`
**Problem:** `memory_commit_archival` with the reformatter code stores entries like `"Context: [unspecified]. Action: [unspecified]. Outcome: [unspecified]."` These are noise.
**Impact:** Memory fills with useless entries that pollute future queries.

### S2-06: No Token/Cost Budget Per Cycle
**File:** `agent_loop.py`
**Problem:** Token usage is logged but not tracked cumulatively. No mechanism to stop a cycle that has spent $50 in API calls. Max tool calls (100) is the only limit, but each call can be expensive.
**Impact:** Runaway spending during degenerate loops.

### S2-07: eval-generator `.ready` File Can Be Stale
**File:** `eval_request.py` line 18
**Problem:** `.ready` is written when eval-generator starts but never deleted on shutdown. If eval-generator crashes, the file persists and `eval_request` thinks it's running.
**Impact:** Eval requests silently dropped. Agent waits 5 minutes for results that never come.

### S2-08: No Deduplication of Tool Call Loops
**File:** `agent_loop.py` lines 372-414
**Problem:** LLM can call the same failing tool 100 times with identical parameters. No cycle detection, no deduplication. Loop continues until `max_tool_calls` is hit.
**Impact:** Wasted tokens and time.

### S2-09: Background Terminal Jobs Have No Lifecycle
**Files:** `tool_terminal.py`, `_internal/job_state.py`
**Problem:** Background jobs run indefinitely. `active_jobs` dict is in-memory only — lost on restart. No timeout, no cleanup, no limit on concurrent jobs.
**Impact:** Zombie processes accumulate.

---

## PART 2: IMPLEMENTATION PLAN

### Priority 1: Prevent System Bricking (S0 fixes)

#### FIX-01: Protected Path Enforcement
**What:** Add a path blacklist to ALL file modification tools.
**Where:** `skills/tool-use/functions/tool_file_edit_diff.py`, `tool_file_write.py`, `tool_terminal.py`
**How:**
```python
# New file: skills/tool-use/functions/_internal/path_guard.py

import os

# Files that must NEVER be modified by the evolution loop
PROTECTED_PATHS = {
    "kernel.py",
    "agent_loop.py",
    "config.json",
    "manifest.json",
    "start.py",
    "requirements.txt",
    ".env",
    ".git",
}

# Directories that must never be modified
PROTECTED_DIRS = {
    "eval-generator",
    "adapters",
    ".git",
}

def is_path_protected(file_path: str, boros_root: str) -> tuple[bool, str]:
    """Returns (is_protected, reason) for a given file path."""
    rel = os.path.relpath(os.path.abspath(file_path), os.path.abspath(boros_root))
    rel_normalized = rel.replace("\\", "/")

    # Check exact file matches
    for protected in PROTECTED_PATHS:
        if rel_normalized == protected or rel_normalized.endswith("/" + protected):
            return True, f"'{protected}' is a protected infrastructure file"

    # Check directory matches
    for protected_dir in PROTECTED_DIRS:
        if rel_normalized.startswith(protected_dir + "/") or rel_normalized == protected_dir:
            return True, f"'{protected_dir}/' is a protected infrastructure directory"

    # Only allow modifications inside skills/ directory
    if not rel_normalized.startswith("skills/"):
        return True, f"Only files under skills/ can be modified. Got: {rel_normalized}"

    return False, ""
```

**Integration:** Every file tool checks `is_path_protected()` before proceeding. Return error if protected.

**Terminal hardening:** Add command filtering to `tool_terminal.py`:
```python
DANGEROUS_PATTERNS = ["rm -rf", "del /s", "rmdir /s", "> kernel.py", "> agent_loop.py",
                      "> config.json", "> manifest.json", "format ", "mkfs"]

def is_command_dangerous(command: str) -> tuple[bool, str]:
    cmd_lower = command.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in cmd_lower:
            return True, f"Command contains dangerous pattern: '{pattern}'"
    return False, ""
```

---

#### FIX-02: Crash-Safe Cycle Recovery
**What:** Ensure bad code is ALWAYS rolled back when a cycle doesn't reach COMMIT cleanly.
**Where:** `skills/loop-orchestrator/functions/loop_start.py`
**How:**

Rewrite crash recovery to be more aggressive:
```python
def _recover_from_crash(boros_dir, kernel):
    """Called when loop_start detects an unfinished cycle."""
    # 1. Always try to rollback from evolution_target snapshot
    target_file = os.path.join(boros_dir, "session", "evolution_target.json")
    if os.path.exists(target_file):
        with open(target_file) as f:
            target = json.load(f)
        snapshot_id = target.get("snapshot_id")
        target_skill = target.get("target_skill")
        if snapshot_id and "forge_rollback" in kernel.registry:
            result = kernel.registry["forge_rollback"](
                {"snapshot_id": snapshot_id, "target": target_skill}, kernel
            )
            print(f"[CRASH RECOVERY] Rolled back {target_skill} to {snapshot_id}: {result.get('status')}")

    # 2. Check if there are pending eval scores we missed
    pending_file = os.path.join(boros_dir, "session", "pending_eval.json")
    if os.path.exists(pending_file):
        # Don't poll — just note it. The eval may have completed.
        # eval_read_scores with no ID will pick up the latest.
        pass

    # 3. Clean up stale session files
    for stale in ["hypothesis.json", "evolution_target.json", "review_feedback.json"]:
        path = os.path.join(boros_dir, "session", stale)
        if os.path.exists(path):
            os.remove(path)

    # 4. Write crash record to evolution_records for learning
    crash_record = {
        "type": "crash_recovery",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "snapshot_rolled_back": snapshot_id if 'snapshot_id' in dir() else None,
        "target_skill": target.get("target_skill") if os.path.exists(target_file) else None,
    }
    records_dir = os.path.join(boros_dir, "memory", "evolution_records")
    os.makedirs(records_dir, exist_ok=True)
    with open(os.path.join(records_dir, f"crash-{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"), "w") as f:
        json.dump(crash_record, f, indent=2)
```

---

#### FIX-03: Per-Skill Boot Isolation
**What:** Don't let one broken skill kill the entire kernel.
**Where:** `kernel.py` `_load_skills()`
**How:**
```python
def _load_skills(self):
    failed_skills = []
    for skill_name in self.manifest["skills"]:
        try:
            # existing loading logic...
            pass
        except Exception as e:
            print(f"[KERNEL] WARNING: Failed to load skill {skill_name}: {e}")
            failed_skills.append(skill_name)
            # Don't raise — continue loading other skills

    if failed_skills:
        print(f"[KERNEL] {len(failed_skills)} skills failed to load: {failed_skills}")
        # Write failed skills to session for the agent to see
        with open(os.path.join(self.boros_root, "session", "failed_skills.json"), "w") as f:
            json.dump(failed_skills, f)
```

---

#### FIX-04: Config/Manifest Schema Validation
**What:** Validate critical JSON files at boot.
**Where:** `kernel.py` `_load_config()`, `_load_manifest()`
**How:**
```python
def _validate_world_model(self):
    """Ensure world_model.json has the required structure."""
    wm_path = self.boros_root / "world_model.json"
    with open(wm_path) as f:
        wm = json.load(f)

    assert "categories" in wm, "world_model.json must have 'categories' key"
    cats = wm["categories"]
    assert isinstance(cats, dict), "'categories' must be a dict"
    assert len(cats) > 0, "'categories' must have at least one category"

    for cat_id, cat_data in cats.items():
        required = ["weight", "anchors", "rubric", "failure_modes", "related_skills"]
        for field in required:
            assert field in cat_data, f"Category '{cat_id}' missing required field '{field}'"
        assert isinstance(cat_data["related_skills"], list), f"'{cat_id}.related_skills' must be a list"
        assert cat_data["weight"] > 0, f"'{cat_id}.weight' must be positive"
```

---

### Priority 2: Enable Real Learning (S1 fixes)

#### FIX-05: Evolution Ledger — Change-to-Outcome Tracking (THE CRITICAL FIX)
**What:** Create a single, append-only ledger that links every code change to its score impact.
**Where:** New file `skills/meta-evolution/functions/_internal/evolution_ledger.py`
**How:**

```python
# evolution_ledger.py — The single source of truth for "what worked?"

import os, json, datetime

LEDGER_FILE = "memory/evolution_ledger.jsonl"

def record_attempt(boros_dir: str, entry: dict):
    """Append one evolution attempt to the ledger."""
    path = os.path.join(boros_dir, LEDGER_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")

def query_ledger(boros_dir: str, target_file: str = None, target_skill: str = None,
                 outcome: str = None, limit: int = 20) -> list:
    """Query past evolution attempts with filters."""
    path = os.path.join(boros_dir, LEDGER_FILE)
    if not os.path.exists(path):
        return []

    entries = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
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
    return query_ledger(boros_dir, target_file=target_file)

def get_skill_stats(boros_dir: str, target_skill: str) -> dict:
    """Get aggregate statistics for a skill's evolution history."""
    entries = query_ledger(boros_dir, target_skill=target_skill, limit=100)
    if not entries:
        return {"attempts": 0, "improvements": 0, "regressions": 0, "neutral": 0}

    stats = {"attempts": len(entries), "improvements": 0, "regressions": 0, "neutral": 0}
    for e in entries:
        outcome = e.get("outcome", "unknown")
        if outcome in stats:
            stats[outcome] += 1

    stats["success_rate"] = stats["improvements"] / max(stats["attempts"], 1)
    stats["last_outcome"] = entries[-1].get("outcome")
    stats["last_approach"] = entries[-1].get("approach")
    return stats
```

**Ledger entry format** (written by `loop_end_cycle`):
```json
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
    "outcome": "improved",
    "review_verdict": "apply",
    "hypothesis_rationale": "..."
}
```

**Integration points:**
1. `loop_end_cycle.py` writes ledger entry after computing outcome
2. `evolve_orient.py` reads ledger to check if a file was recently modified without improvement
3. New tool `evolve_query_ledger` exposed to the LLM for explicit queries
4. System prompt injects regressions from ledger as warnings

---

#### FIX-06: Programmatic Anti-Brute-Force
**What:** Block modifications to files that recently regressed.
**Where:** `skills/meta-evolution/functions/evolve_propose.py`
**How:**
```python
# In evolve_propose, before creating proposal:
from ._internal.evolution_ledger import get_file_history

def _check_brute_force(boros_dir, target_file):
    """Check if this file was recently modified without improvement."""
    history = get_file_history(boros_dir, target_file)
    if not history:
        return None  # No history, safe to proceed

    recent = history[-3:]  # Last 3 attempts on this file
    recent_failures = [e for e in recent if e.get("outcome") in ("regressed", "neutral")]

    if len(recent_failures) >= 2:
        return {
            "status": "blocked",
            "message": f"Anti-brute-force: {target_file} was modified {len(recent_failures)} "
                       f"times recently without improvement. Try a different file or approach.",
            "recent_attempts": recent_failures
        }
    return None
```

---

#### FIX-07: Automatic Regression Rollback in loop_end_cycle
**What:** Make regression detection and rollback happen automatically at the end of every cycle, not dependent on the LLM calling it.
**Where:** `skills/loop-orchestrator/functions/loop_end_cycle.py`
**How:**

Add to `loop_end_cycle` after score comparison:
```python
# After computing outcome...
if outcome == "regressed":
    # Auto-rollback: restore the snapshot
    snapshot_id = None
    target_file = os.path.join(boros_dir, "session", "evolution_target.json")
    if os.path.exists(target_file):
        with open(target_file) as f:
            target = json.load(f)
        snapshot_id = target.get("snapshot_id")
        target_skill = target.get("target_skill")

    if snapshot_id and "forge_rollback" in kernel.registry:
        rollback_result = kernel.registry["forge_rollback"](
            {"snapshot_id": snapshot_id, "target": target_skill}, kernel
        )
        record["auto_rollback"] = {
            "snapshot_id": snapshot_id,
            "result": rollback_result.get("status")
        }
        print(f"[AUTO-ROLLBACK] {target_skill} regressed ({delta:+.3f}). "
              f"Restored snapshot {snapshot_id}.")
```

---

#### FIX-08: Activate the Knowledge Graph
**What:** Wire the existing KG into the evolution loop so it captures structured facts.
**Where:** `loop_end_cycle.py`, `evolve_orient.py`, `agent_loop.py`
**How:**

Write KG triples at the end of each cycle:
```python
# In loop_end_cycle, after computing outcome:
if "memory_kg_write" in kernel.registry:
    kg = kernel.registry["memory_kg_write"]
    cycle = state.get("cycle", 0)

    # Record score
    for cat, score in score_after.items():
        kg({"subject": cat, "predicate": "has_score",
            "object": str(score), "cycle": cycle}, kernel)

    # Record what was modified
    if target_skill:
        kg({"subject": target_skill, "predicate": "was_modified",
            "object": approach or "unknown", "cycle": cycle}, kernel)

    # Record causal link
    if target_skill and target_cat:
        kg({"subject": target_skill, "predicate": "caused_delta_in",
            "object": f"{target_cat}:{delta:+.3f}", "cycle": cycle,
            "metadata": {"outcome": outcome}}, kernel)
```

Read KG during REFLECT:
```python
# In evolve_orient, query the KG for the weakest category:
if "memory_kg_query" in kernel.registry:
    history = kernel.registry["memory_kg_query"](
        {"subject": weakest_skill, "predicate": "was_modified", "include_history": True}, kernel
    )
    # Include modification history in candidates output
```

---

#### FIX-09: Fix Review Board Fallback
**What:** When meta_eval LLM is unavailable, default to REJECT (not approve).
**Where:** `skills/meta-evaluation/functions/review_proposal.py`
**How:**
```python
# Change the fallback from:
verdict = "apply"
reason = "No meta-eval LLM configured. Rule-based approval."

# To:
verdict = "reject"
reason = "No meta-eval LLM available. Cannot verify proposal quality. Rejecting by default."
```

---

#### FIX-10: Surface Failures in System Prompt
**What:** The system prompt should highlight regressions and blocked files prominently.
**Where:** `agent_loop.py` system prompt construction (lines 116-148)
**How:**

Add a new section after the hypothesis outcomes:
```python
# Load regression warnings from ledger
from skills.meta_evolution.functions._internal.evolution_ledger import query_ledger

regressions = query_ledger(boros_dir, outcome="regressed", limit=10)
if regressions:
    prompt += "\n\n## REGRESSION WARNINGS — DO NOT REPEAT THESE\n"
    for r in regressions:
        prompt += (f"- Cycle {r['cycle']}: Changed {r['target_file']} "
                   f"({r['approach'][:80]}...) → REGRESSED {r['delta']:+.3f}\n")

# Load blocked files (anti-brute-force)
blocked = []
for r in query_ledger(boros_dir, limit=50):
    if r.get("outcome") in ("regressed", "neutral"):
        blocked.append(r.get("target_file"))
if blocked:
    prompt += f"\n## BLOCKED FILES (recently failed, try different approach)\n"
    for f in set(blocked):
        prompt += f"- {f}\n"
```

---

#### FIX-11: Enforce Hypothesis Requirement
**Where:** `skills/meta-evolution/functions/evolve_propose.py`
**How:**
```python
# At the top of evolve_propose:
hyp_file = os.path.join(boros_dir, "session", "hypothesis.json")
if not os.path.exists(hyp_file):
    return {"status": "error",
            "message": "Cannot create proposal without a hypothesis. Call reflection_write_hypothesis first."}

with open(hyp_file) as f:
    hypothesis = json.load(f)

if not hypothesis.get("rationale") or not hypothesis.get("expected_improvement"):
    return {"status": "error",
            "message": "Hypothesis must have 'rationale' and 'expected_improvement' fields."}
```

---

#### FIX-12: Dampen High-Water Marks
**What:** Use a smoothed high-water mark instead of absolute maximum.
**Where:** `skills/eval-bridge/functions/eval_update_high_water.py`
**How:**
```python
def eval_update_high_water(params: dict, kernel=None) -> dict:
    """Update high-water marks using EMA (exponential moving average) dampening."""
    ALPHA = 0.7  # Weight of new score vs. existing high-water

    scores = params.get("scores", {})
    # ... read existing marks ...

    updated = {}
    for cat, score in scores.items():
        if not isinstance(score, (int, float)):
            continue
        current_hw = marks.get(cat, 0.0)
        if score > current_hw:
            # Dampen: don't jump to the spike, blend toward it
            new_hw = current_hw * (1 - ALPHA) + score * ALPHA
            marks[cat] = round(new_hw, 4)
            updated[cat] = marks[cat]
        # Also allow slow decay if consistently below
        elif score < current_hw - 0.1:  # Significantly below
            decay = 0.005  # Decay by 0.5% per cycle
            marks[cat] = round(max(score, current_hw - decay), 4)

    # ... write back ...
```

---

### Priority 3: Improve Quality (S2 fixes)

#### FIX-13: Score History Rotation
**Where:** `skills/eval-bridge/functions/eval_read_scores.py`
**How:** After appending to `score_history.jsonl`, check file size:
```python
MAX_HISTORY_LINES = 500

def _rotate_score_history(score_hist):
    """Keep only the last MAX_HISTORY_LINES entries."""
    if not os.path.exists(score_hist):
        return
    with open(score_hist) as f:
        lines = f.readlines()
    if len(lines) > MAX_HISTORY_LINES:
        # Archive old entries
        archive = score_hist + ".archive"
        with open(archive, "a") as f:
            f.writelines(lines[:-MAX_HISTORY_LINES])
        # Keep recent
        with open(score_hist, "w") as f:
            f.writelines(lines[-MAX_HISTORY_LINES:])
```

---

#### FIX-14: Snapshot Retention Enforcement
**Where:** `skills/skill-forge/functions/forge_snapshot.py`
**How:**
```python
def _enforce_retention(snapshots_dir, keep_last=10):
    """Delete old snapshots, keeping the most recent N."""
    if not os.path.isdir(snapshots_dir):
        return
    dirs = sorted(
        [d for d in os.listdir(snapshots_dir) if d.startswith("snap-")],
        key=lambda d: os.path.getmtime(os.path.join(snapshots_dir, d)),
        reverse=True
    )
    for old in dirs[keep_last:]:
        shutil.rmtree(os.path.join(snapshots_dir, old), ignore_errors=True)
```

---

#### FIX-15: Difficulty-Aware Task Generation
**Where:** `eval-generator/eval_generator.py` task generation prompt
**How:** Add difficulty to the task generation prompt:
```python
# In _generate_tasks:
difficulty = milestone_data.get("difficulty", 3)
prompt += f"\n\nDifficulty level: {difficulty}/10. "
if difficulty <= 3:
    prompt += "Create a straightforward task testing basic capability."
elif difficulty <= 6:
    prompt += "Create a moderately challenging task requiring multi-step reasoning."
elif difficulty <= 8:
    prompt += "Create a complex task with edge cases and constraints."
else:
    prompt += "Create an expert-level task that pushes the limits of the capability."
```

---

#### FIX-16: Reject Empty/Placeholder Experiences
**Where:** `skills/memory/functions/memory_commit_archival.py`
**How:**
```python
# After the required_phrases check:
if "[unspecified]" in content or "[missing" in content.lower():
    return {"status": "error",
            "message": "Content contains placeholder text. Provide actual details."}

# Also reject very short content
if len(content.strip()) < 50:
    return {"status": "error",
            "message": f"Content too short ({len(content.strip())} chars). Minimum 50 chars for meaningful memory."}
```

---

#### FIX-17: Tool Call Deduplication
**Where:** `agent_loop.py` dispatch loop
**How:**
```python
# Track recent tool calls
recent_calls = []  # list of (tool_name, params_hash)

def _is_duplicate_call(name, params, recent_calls, window=5):
    """Check if this exact call was made in the last N calls."""
    import hashlib
    params_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
    key = (name, params_hash)
    if key in recent_calls[-window:]:
        return True
    recent_calls.append(key)
    return False

# In the dispatch loop:
if _is_duplicate_call(tool_name, tool_params, recent_calls):
    result = {"status": "error",
              "message": f"Duplicate call: {tool_name} with same parameters was called recently. Try a different approach."}
else:
    result = self.dispatch_tool(tool_name, tool_params)
```

---

#### FIX-18: eval-generator Health Heartbeat
**Where:** `eval-generator/eval_generator.py`, `skills/eval-bridge/functions/eval_request.py`
**How:**

In eval_generator, update heartbeat every processing loop:
```python
# In eval_generator main loop:
heartbeat_file = os.path.join(shared_dir, ".heartbeat")
with open(heartbeat_file, "w") as f:
    f.write(datetime.datetime.utcnow().isoformat())
```

In eval_request, check heartbeat freshness:
```python
heartbeat_file = os.path.join(boros_dir, "eval-generator", "shared", ".heartbeat")
if os.path.exists(heartbeat_file):
    mtime = os.path.getmtime(heartbeat_file)
    age_seconds = time.time() - mtime
    if age_seconds > 120:  # 2 minutes stale
        return {"status": "error",
                "message": f"Eval-generator heartbeat is {age_seconds:.0f}s old. It may have crashed. Restart it."}
```

---

#### FIX-19: Token Budget Per Cycle
**Where:** `agent_loop.py`
**How:**
```python
# In agent_loop __init__:
self.cycle_token_budget = config.get("max_tokens_per_cycle", 500_000)
self.cycle_tokens_used = 0

# After each LLM call:
self.cycle_tokens_used += response.usage.input_tokens + response.usage.output_tokens
if self.cycle_tokens_used > self.cycle_token_budget:
    self.log(f"[BUDGET] Token budget exceeded ({self.cycle_tokens_used}/{self.cycle_token_budget}). Forcing cycle end.")
    self._ensure_cycle_committed()
    break
```

---

#### FIX-20: Background Job Lifecycle
**Where:** `skills/tool-use/functions/tool_terminal.py`
**How:**
```python
MAX_BACKGROUND_JOBS = 3
JOB_TIMEOUT_SECONDS = 300  # 5 minutes

def _cleanup_expired_jobs():
    """Kill background jobs that exceeded their timeout."""
    import time
    now = time.time()
    expired = [jid for jid, info in active_jobs.items()
               if now - info.get("started_at", 0) > JOB_TIMEOUT_SECONDS]
    for jid in expired:
        try:
            active_jobs[jid]["process"].kill()
        except Exception:
            pass
        del active_jobs[jid]

# Before spawning new background job:
_cleanup_expired_jobs()
if len(active_jobs) >= MAX_BACKGROUND_JOBS:
    return {"status": "error", "message": f"Max {MAX_BACKGROUND_JOBS} background jobs. Kill one first."}
```

---

## PART 3: IMPLEMENTATION ORDER

### Phase 1 — Stop the Bleeding (Do First)
| Fix | Issue | Effort | Files Changed |
|-----|-------|--------|---------------|
| FIX-01 | Path protection | Medium | 3 files + 1 new |
| FIX-02 | Crash-safe recovery | Medium | 1 file |
| FIX-03 | Per-skill boot isolation | Small | 1 file |
| FIX-07 | Auto regression rollback | Small | 1 file |
| FIX-09 | Review board fallback | Tiny | 1 file |
| FIX-11 | Hypothesis enforcement | Small | 1 file |

### Phase 2 — Enable Real Learning (Do Second)
| Fix | Issue | Effort | Files Changed |
|-----|-------|--------|---------------|
| FIX-05 | Evolution ledger | Large | 1 new + 3 integrations |
| FIX-06 | Anti-brute-force | Medium | 1 file |
| FIX-08 | Activate knowledge graph | Medium | 2 files |
| FIX-10 | Surface failures in prompt | Medium | 1 file |
| FIX-12 | Dampen high-water marks | Small | 1 file |

### Phase 3 — Harden & Polish (Do Third)
| Fix | Issue | Effort | Files Changed |
|-----|-------|--------|---------------|
| FIX-04 | Schema validation | Small | 1 file |
| FIX-13 | Score history rotation | Small | 1 file |
| FIX-14 | Snapshot retention | Small | 1 file |
| FIX-15 | Difficulty scaling | Small | 1 file |
| FIX-16 | Reject empty experiences | Tiny | 1 file |
| FIX-17 | Tool call dedup | Small | 1 file |
| FIX-18 | Heartbeat check | Small | 2 files |
| FIX-19 | Token budget | Small | 1 file |
| FIX-20 | Job lifecycle | Small | 1 file |

---

## PART 4: THE NORTH STAR — WHAT "REAL SELF-EVOLUTION" LOOKS LIKE

After all fixes are implemented, this is how a cycle should flow:

### REFLECT (Informed by History)
1. `loop_start` — detects any crash, auto-rolls back, writes crash record
2. `eval_read_scores` — gets latest scores (with `pending_eval.json` fallback)
3. `reflection_analyze_trace` — finds weakest category
4. **System prompt now includes:**
   - Last 10 hypothesis outcomes (formatted with IMPROVED/REGRESSED)
   - **REGRESSION WARNINGS** — files that recently regressed (from evolution ledger)
   - **BLOCKED FILES** — files that failed twice (anti-brute-force)
   - Knowledge graph facts for the target skill
5. `evolve_orient` — finds candidates, **filtering out blocked files**
6. `reflection_write_hypothesis` — required before proceeding (enforced)

### EVOLVE (Guided by Learning)
7. `forge_snapshot` — takes backup (with retention enforcement)
8. `evolve_propose` — creates proposal, **checks anti-brute-force**, **requires hypothesis**
9. `review_proposal` — LLM review (defaults to REJECT if unavailable)
10. `evolve_apply` — applies and hot-reloads (with proper transitive reload)

### EVAL (Reliable Scoring)
11. `eval_request` — writes `pending_eval.json` with cycle number
12. `eval_read_scores` — polls with fallback to `pending_eval.json` (no hallucination stalls)
13. **Scores are dampened** — high-water marks use EMA, not absolute max

### COMMIT (Guaranteed Outcome Recording)
14. `eval_check_regression` — called automatically by `loop_end_cycle`
15. **If regressed: auto-rollback fires**, snapshot restored, no LLM decision needed
16. **Evolution ledger entry written** — links file → change → score_before → score_after → outcome
17. **KG triples written** — `has_score`, `was_modified`, `caused_delta_in`
18. `eval_check_milestone` — advances if consecutive threshold met
19. Hypothesis archived with full outcome data
20. Session cleaned for next cycle

### THE RESULT
- Every cycle produces a ledger entry linking change → outcome
- The system prompt warns against repeating failures
- Anti-brute-force blocks dead-end approaches programmatically
- Crashes always roll back to known-good state
- No infrastructure file can be accidentally corrupted
- The knowledge graph accumulates structured causal knowledge
- High-water marks don't ratchet to noise spikes
- Milestones face progressively harder tasks

**This is genuine self-evolution:** not just random mutation and selection, but *informed* evolution where every cycle builds on the structured knowledge of all previous cycles.
