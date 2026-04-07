# Eval-Generator: Implementation Audit

Analysis date: 2026-04-07. Based on full code read of `eval-generator/`, `skills/eval-bridge/`, `skills/loop-orchestrator/`, and live cycle logs from cycles 1–2.

---

## System Overview

Two-process architecture communicating via filesystem:

```
Main Boros loop               eval-generator (separate process)
───────────────               ────────────────────────────────
eval_request()   ──────────→  shared/requests/{id}.json
                               polls every 2s, processes request
                               generates task via LLM
                               runs sandbox agent (up to 3 iterations)
                               grades via 3-layer pipeline
eval_read_scores() ←─────────  shared/results/{id}.json
                               (main loop polls up to 5 min)
```

**3-layer grading pipeline:**
1. **Deterministic** — fatal errors in transcript or zero files created → score 0.0
2. **Structural** — file sizes, tool call count, completion signals → contributes up to 0.5
3. **LLM grader** — scores rubric level 1–4, blended 70/30 with structural

**Status: Core pipeline is functional.** Two evals ran end-to-end, tasks generated, sandbox executed, graded, scores returned to main loop.

---

## Bugs to Fix

### BUG 1 — High-water marks never updated (CRITICAL)

**File:** `skills/loop-orchestrator/functions/loop_end_cycle.py`
**Also:** `skills/eval-bridge/state/high_water_marks.json`

**What happens:** `high_water_marks.json` still shows `{reasoning: 0.0, web_search: 0.0}` after reasoning scored 0.645 in cycle 1. `loop_end_cycle` — which persists high-water marks — was never called. The agent ended its turn naturally after `eval_check_regression`, skipping the COMMIT stage entirely. So in cycle 2, `evolve_orient` told Boros it improved by +0.645 from baseline 0.0 (not from the real prior score of 0.5). Regression detection is broken until a full COMMIT runs.

**Impact:** Boros can never detect regressions in practice. Any score above 0.0 looks like an improvement. The entire safety mechanism of `auto_pause_on_regression` is nullified.

**Fix options:**
- A: Make `loop_end_cycle` idempotent and call it automatically at cycle completion in `agent_loop.py` if the LLM ends its turn without calling it (safety net).
- B: Have `eval_check_regression` update high-water marks inline on success so they're not dependent on COMMIT running.
- C: Both — belt and suspenders.

**Recommended:** Option A. Add a post-cycle hook in `agent_loop.py`: if `loop_state.stage != None` when the LLM turn ends naturally, call `loop_end_cycle` automatically.

---

### BUG 2 — `eval-generator/config.json` is dead config

**File:** `eval-generator/config.json`

**What happens:** `eval_generator.py` loads config from `boros_root/config.json` (the main Boros config):
```python
self.config_path = os.path.join(boros_root, "config.json")
```
The file `eval-generator/config.json` (containing `max_eval_turns: 20`, `scoring.outcome_weight: 0.6`, `scoring.quality_weight: 0.4`) is never opened by anything.

**Impact:** Config changes in `eval-generator/config.json` have zero effect. Developers editing it get no feedback that it's ignored.

**Fix:** Either delete `eval-generator/config.json` and move its settings into main `config.json`, or change `eval_generator.py` to load from its local config first and fall back to boros root config.

---

### BUG 3 — `difficulty-config.json` is dead config

**File:** `eval-generator/difficulty-config.json`

**What happens:** The file contains `{difficulty_level: 2, tests_per_category: 3}` but `eval_generator.py` hardcodes `difficulty_level: 5` in result JSON and `tests_per_category` is never used (only one task is generated per category per eval).

**Impact:** Difficulty scaling and multi-test averaging don't exist yet. The file implies they were planned but never implemented.

**Fix:** Either implement difficulty scaling in `_generate_task()` and multi-test averaging in `_eval_single_category()`, or delete the file and add a TODO comment in code.

---

### BUG 4 — Scratchpad tools unreachable in `tool_dispatcher.py` (dead code)

**File:** `eval-generator/tool_dispatcher.py`, lines 82–108

**What happens:** The scratchpad branches (`scratchpad_write`, `scratchpad_read`, `scratchpad_clear`) are nested inside an `elif` that only matches `("write_file", "read_file", "list_directory")`. They can never execute:

```python
elif tool_name in ("write_file", "read_file", "list_directory"):
    if tool_name == "write_file": ...
    elif tool_name == "read_file": ...
    elif tool_name == "list_directory": ...
    elif tool_name == "scratchpad_write":   # DEAD — never reached
        ...
    elif tool_name == "scratchpad_read":    # DEAD — never reached
        ...
    elif tool_name == "scratchpad_clear":   # DEAD — never reached
        ...
```

**Impact:** Sandbox agents calling scratchpad tools fall through to `return {"status": "error", "error": "unknown tool"}`.

**Fix:** Move scratchpad cases to their own top-level `elif` block.

---

### BUG 5 — LLM grader truncates transcript at 3,000 chars

**File:** `eval-generator/eval_generator.py`, line 209

**What happens:**
```python
f"## Agent Transcript\n{transcript[:3000]}\n\n"
```
With 3 agent iterations and typical tool output sizes, transcripts easily exceed 3,000 chars. The grader may score on an incomplete transcript — missing the actual tool results and file creation evidence in the tail.

**Impact:** LLM grader has degraded accuracy. A task that produces files may appear incomplete to the grader if the `write_file` confirmation fell past the 3,000-char cut. This could cause good performance to score low.

**Fix:** Increase limit (8,000–12,000 is reasonable for Gemini Flash), or send the transcript tail (last N chars) rather than the head, or summarize the middle.

---

### BUG 6 — `outcome_score` and `quality_score` are always identical

**File:** `eval-generator/eval_generator.py`, lines 391–398 and 425–432

**What happens:** Both scores are set to the same `score` value from `_grade_sandbox`:
```python
"outcome_score": score,
"quality_score": score,   # same value every time
```
The world model intends these to measure separate dimensions (task outcome vs. reasoning quality). The grader's JSON response has `quality_reason` and `outcome_details` as separate fields but they're collapsed into one number before storage.

**Impact:** Downstream analysis and weighted scoring lose the distinction. The `outcome_weight: 0.5 / quality_weight: 0.5` split in result JSON is meaningless.

**Fix:** In `_grade_sandbox`, return separate outcome and quality scores. The LLM grader prompt should ask for both. Alternatively, document explicitly that this system uses a unified score and remove the misleading dual-field structure.

---

### BUG 7 — `execute_command` tool is stubbed

**File:** `eval-generator/tool_dispatcher.py`, lines 78–80

**What happens:**
```python
elif tool_name == "execute_command":
    return {"status": "ok", "stdout": "stub output", "stderr": "", "returncode": 0}
```
Any sandbox agent calling `execute_command` gets fake output regardless of what command was specified.

**Impact:** Low risk currently — both observed evals used `tool_terminal` (which is properly implemented). But if a generated task leads the agent to use `execute_command`, the task appears to succeed with nothing actually executed, corrupting the score.

**Fix:** Either implement it the same as `tool_terminal` (subprocess in sandbox_path), or remove the tool from the available tools list so the agent never gets offered it.

---

## What's Working Correctly

| Component | Status |
|---|---|
| Request/response filesystem pipeline | Working |
| Task generation from world_model (LLM) | Working |
| Sandbox path isolation / traversal protection | Working |
| Blocked prefixes (loop_, evolve_, eval_, forge_) | Working |
| 3-layer grading pipeline | Working |
| `score_history.jsonl` append | Working |
| `eval_check_regression` logic | Working (data is broken — see Bug 1) |
| Concurrent category evaluation (ThreadPoolExecutor) | Working |
| Request expiry / stale request cleanup | Working |
| World model hot-reload on each request | Working |
| Skill hot-reload before each eval | Working |
| Sandbox cleanup after eval | Working |

---

## Priority Order for Fixes

1. **Bug 1** — High-water marks (CRITICAL: breaks safety + regression detection)
2. **Bug 4** — Scratchpad dead code (easy 5-min fix)
3. **Bug 7** — Stubbed execute_command (easy: either implement or remove from tool list)
4. **Bug 5** — Transcript truncation (affects scoring accuracy)
5. **Bug 6** — Collapsed outcome/quality scores (affects metric depth)
6. **Bug 2** — Dead eval config (cleanup / correctness)
7. **Bug 3** — Dead difficulty config (implement or delete)
