# Boros — Full Architecture Audit & Suggestions

> Exhaustive file-by-file analysis with concrete changes to make Boros a robust, open-source, self-evolving agent.

---

## Table of Contents

1. [Audit Summary](#audit-summary)
2. [Critical Bugs — Fix Immediately](#critical-bugs)
3. [Architecture Gaps — Core Evolution Loop](#architecture-gaps)
4. [Eval System — Making Scores Trustworthy](#eval-system)
5. [Adapter Layer — Multi-LLM Robustness](#adapter-layer)
6. [Skill-by-Skill Findings](#skill-by-skill-findings)
7. [New Features for World-Class Self-Evolution](#new-features)
8. [Open-Source Readiness](#open-source-readiness)
9. [Suggested Execution Order](#execution-order)

---

## 1. Audit Summary <a name="audit-summary"></a>

**Files audited:** 87 Python files, 15 skill directories, 5 adapter providers, eval-generator, kernel, agent_loop, all config/manifest files.

**Overall verdict:** The evolution loop machinery is real and well-architected. The 4-stage cycle (REFLECT > EVOLVE > EVAL > COMMIT) is properly implemented across `agent_loop.py`, `cycle_prompt.md`, and the orchestration skills. The modular skill system, snapshot/rollback, and hot-reload are genuine working infrastructure.

**What holds it back from being world-class:**

- 12 bugs that would crash at runtime
- World model `related_skills` don't map to actual skill directories
- Eval grading is 100% LLM-subjective with no deterministic verification
- Meta-evaluation review board defaults to approval on any failure
- Reasoning skill is mostly stubs
- No BOROS.md (the LLM's identity document) ships with the repo
- Memory claims vector search but only does keyword grep
- No process orchestration (eval-generator must be started separately with no docs)

---

## 2. Critical Bugs — Fix Immediately <a name="critical-bugs"></a>

### BUG-01: `memory_page_out.py` — Hardcoded relative path

**File:** `skills/memory/functions/memory_page_out.py`, line 7
**Problem:** Uses `os.path.join("memory", "sessions")` instead of `os.path.join(boros_dir, "memory", "sessions")`. Fails when CWD is not the boros root.
**Fix:** Use `boros_dir` derived from `kernel.boros_root` like every other function does.

### BUG-02: `reason_evaluate_options.py` — Wrong function signature

**File:** `skills/reasoning/functions/reason_evaluate_options.py`, line 4
**Problem:** Signature is `def reason_evaluate_options(options: list[str], criteria: str)` but the kernel dispatches `(params: dict, kernel)`. This function will crash on every call.
**Fix:** Change signature to `def reason_evaluate_options(params: dict, kernel=None)` and extract `options` and `criteria` from `params`.

### BUG-03: `reason_decompose.py` — Undefined variable in exception handler

**File:** `skills/reasoning/functions/reason_decompose.py`, line 27
**Problem:** `except` block references `text` which is defined inside the `try` block. If JSON parsing fails before `text` is assigned, `UnboundLocalError` is raised inside the exception handler itself.
**Fix:** Initialize `text = ""` before the try block.

### BUG-04: `review_proposal.py` — Regex can't handle nested JSON braces

**File:** `skills/meta-evaluation/functions/review_proposal.py`, line 49
**Problem:** `re.search(r'\{[^}]+\}', response_text)` breaks on `{"verdict": "apply", "reason": "good {code}"}` because `[^}]` stops at the first `}`.
**Fix:** Use a proper JSON extraction approach:

```python
import json
# Find the first { and try progressively longer substrings
start = response_text.find('{')
if start != -1:
    for end in range(len(response_text), start, -1):
        try:
            review = json.loads(response_text[start:end])
            break
        except json.JSONDecodeError:
            continue
```

### BUG-05: `reason_generate_plan.py` — Greedy regex captures garbage

**File:** `skills/reasoning/functions/reason_generate_plan.py`, line 54
**Problem:** `re.search(r'\{.*\}', text_content, re.DOTALL)` is greedy and captures from first `{` to the absolute last `}` in the entire response, including any trailing text.
**Fix:** Same JSON extraction as BUG-04.

### BUG-06: `tool_apply_patch.py` — Missing CWD in subprocess

**File:** `skills/tool-use/functions/tool_apply_patch.py`, line 24
**Problem:** `subprocess.run(["git", "apply", ...])` runs without `cwd` parameter. Applies patches relative to whatever the current working directory happens to be.
**Fix:** Add `cwd=str(kernel.boros_root)` to the subprocess call.

### BUG-07: `memory_page_in.py` — Calls non-existent kernel methods

**File:** `skills/memory/functions/memory_page_in.py`, lines 21, 26, 31, 36
**Problem:** Calls `kernel.log_error()` and `kernel.log_warn()` which don't exist on `BorosKernel`. Will raise `AttributeError`.
**Fix:** Either add `log_error`/`log_warn` methods to `BorosKernel`, or replace with `print()` (which is what every other skill function uses).

### BUG-08: `memory_page_in.py` — Bare `except: pass` clauses

**File:** `skills/memory/functions/memory_page_in.py`, lines 44-45, 50-52, 58-59
**Problem:** Swallows ALL exceptions including `KeyboardInterrupt`, `SystemExit`, `MemoryError`. Silently hides bugs.
**Fix:** Change to `except Exception:` at minimum. Better: `except (json.JSONDecodeError, OSError) as e:` and log the error.

### BUG-09: `memory_search_sql.py` — Bare `except: pass`

**File:** `skills/memory/functions/memory_search_sql.py`, line 20
**Problem:** Same as BUG-08. File I/O errors silently ignored, returning incomplete search results with no indication.
**Fix:** Catch specific exceptions and include error info in the return dict.

### BUG-10: `loop_end_cycle.py` — Bare `except: pass`

**File:** `skills/loop-orchestrator/functions/loop_end_cycle.py`, line 42
**Problem:** Silently ignores errors when cleaning session files.
**Fix:** Catch `OSError` specifically.

### BUG-11: `evolve_orient.py` — Bare `except:` on line 91

**File:** `skills/meta-evolution/functions/evolve_orient.py`, line 91
**Problem:** Silent failure when reading evolution records.
**Fix:** Catch `(json.JSONDecodeError, OSError)`.

### BUG-12: `reason_check_logic.py` — Complete no-op

**File:** `skills/reasoning/functions/reason_check_logic.py`
**Problem:** Returns `{"status": "ok", "note": "Logic checking is performed by the LLM..."}` regardless of input. The LLM will call this tool expecting analysis and get nothing useful.
**Fix:** Either implement real logic checking (call the LLM like `reason_decompose` does) or remove it from `tool_schemas.py` and `manifest.json` so the LLM doesn't waste tool calls on it.

---

## 3. Architecture Gaps — Core Evolution Loop <a name="architecture-gaps"></a>

### GAP-01: Missing BOROS.md — The LLM has no identity

`agent_loop.py` line 33 loads `BOROS.md` as the primary system instruction. This file doesn't ship with the repo. Without it, the LLM running the evolution loop has no identity, no rules, no behavioral constraints — just the `cycle_prompt.md` instructions.

**Suggestion:** Create a `BOROS.md` that ships with the repo. It should contain:

- Boros's identity and operating principles
- Constraints (don't modify kernel/adapters, don't break infrastructure skills)
- The skill-first philosophy
- How to read and interpret evaluation scores
- How to think about SKILL.md modifications vs code changes
- Anti-patterns to avoid (cosmetic changes, infinite rewrites)

This is arguably the most important missing file because it's the AI's brain.

### GAP-02: World model `related_skills` don't map to actual skills

`world_model.json` defines:

- `reasoning.related_skills`: `["planning", "decision_making", "problem_solving"]`
- `web_search.related_skills`: `["information_retrieval", "source_evaluation", "knowledge_extraction"]`

None of these exist as skill directories. The actual skills are `reasoning` and `web-research`.

**What happens:** `evolve_orient()` line 76 checks `skill_name in related_skills` — this will NEVER match because `"reasoning" not in ["planning", "decision_making", "problem_solving"]`. The priority boost on line 104-105 never fires. Evolution targets are effectively random.

**Fix (two options):**

Option A — Map related_skills to real skill names:

```json
"related_skills": ["reasoning"]
```

```json
"related_skills": ["web-research"]
```

Option B (better) — Change `evolve_orient()` to also match by skill directory name similarity, or add a `skill_mapping` field in world_model.json:

```json
"skill_mapping": {
  "planning": "reasoning",
  "decision_making": "reasoning",
  "problem_solving": "reasoning"
}
```

### GAP-03: No process orchestration for eval-generator

The eval-generator is a completely separate Python process. There's no:

- Script to start both kernel + eval-generator together
- Health check from the kernel to verify eval-generator is running
- Auto-start mechanism
- Documentation in README on how to run the eval-generator

A user cloning this repo and running `python kernel.py` will hit a 5-minute timeout on `eval_read_scores` and have no idea why.

**Suggestion:**

1. Add a `start.py` (or `run.py`) that launches both processes:

```python
import subprocess, sys
eval_proc = subprocess.Popen([sys.executable, "eval-generator/eval_generator.py"])
# Then start kernel
from kernel import BorosKernel
kernel = BorosKernel()
# ...
```

2. Or integrate the eval-generator as a thread within the kernel process
3. At minimum, add a health check in `eval_request()` that warns if `eval-generator/shared/.ready` doesn't exist

### GAP-04: Meta-evaluation defaults to approval on ALL failures

`review_proposal.py` lines 60-63:

```python
except Exception as e:
    verdict = "apply"  # <-- This is the problem
    reason = f"Meta-eval LLM call failed ({e}), defaulting to apply."
```

And line 56:

```python
else:
    verdict = "apply"  # Unparseable response → still approved
```

This means: API timeout? Approved. Rate limit? Approved. Invalid JSON? Approved. The review board is a rubber stamp when anything goes wrong.

**Suggestion:** Default to `"reject"` on failure, not `"apply"`. The principle should be: if you can't verify it's safe, don't apply it. The LLM will try again next cycle.

```python
except Exception as e:
    verdict = "reject"
    reason = f"Meta-eval unavailable ({e}). Rejecting for safety — will retry next cycle."
```

### GAP-05: `reflection_analyze_trace.py` has hardcoded category logic

Lines 111-139 contain special-case handling for `"memory_continuity"` and `"reasoning_architecture"` — categories that don't even exist in the current world model. This code does nothing for actual categories like `"reasoning"` and `"web_search"`.

**Suggestion:** Remove hardcoded category logic entirely. Instead, pull actionable recommendations from the world model itself. Each category already has `failure_modes`, `anchors`, and `rubric` — use those to generate dynamic recommendations:

```python
cat_data = active_categories.get(category, {})
failure_modes = cat_data.get("failure_modes", [])
anchors = cat_data.get("anchors", [])
recommendation += f"**Known failure modes:** {', '.join(failure_modes)}\n"
recommendation += f"**Target anchors:** {', '.join(anchors)}\n"
```

### GAP-06: Score history never resets for fresh world model categories

When a user changes `world_model.json` (adds/removes categories), `score_history.jsonl` still contains entries for old categories. `reflection_analyze_trace` correctly filters by active categories (line 67), but `eval_read_scores` appends raw results that may reference stale categories.

**Suggestion:** Add a `score_history_migrate()` function or have `_sync_world_model_state` in kernel.py also annotate the score history with a generation marker so old entries can be distinguished.

### GAP-07: No cycle counter increment

`loop_end_cycle.py` reads `state["cycle"]` but never increments it. `loop_start.py` is the one that increments. But if a cycle crashes between start and end, the cycle counter stays at the crashed number. There's no crash recovery to detect and clean up half-finished cycles.

**Suggestion:** Add crash recovery in `loop_start()`:

- Check if the previous cycle's `stage` is not `None` (meaning it never ended)
- If so, log a warning and reset state before starting a new cycle
- Optionally trigger rollback if a snapshot was active

---

## 4. Eval System — Making Scores Trustworthy <a name="eval-system"></a>

### EVAL-01: Grading is 100% LLM-subjective

`eval_generator.py` `_grade_sandbox()` (line 140) asks the LLM to assign a 0.0-1.0 score. There are only two objective gates:

- `"Error:" in transcript` → 0.0
- `len(file_list) == 0` → 0.0

Everything else is vibes. The LLM could give 0.9 to garbage output.

**Suggestion — Add deterministic scoring layers:**

1. **Output verification:** Check if expected output files exist and have non-empty content
2. **Code execution:** If the task was "write a script", actually run it and check exit code
3. **Pattern matching:** For reasoning tasks, check if the output contains structured elements (numbered steps, explicit alternatives, constraint mentions)
4. **Rubric anchoring:** Instead of asking the LLM for a float, give it the actual 4-level rubric from `world_model.json` and ask it to pick a level (1-4). This constrains the output space and makes scores more consistent.

Example improved grading:

```python
def _grade_sandbox(self, transcript, category_id, workspace_dir):
    # Layer 1: Objective checks
    deterministic_score = self._check_objective_criteria(workspace_dir, transcript)
    if deterministic_score == 0.0:
        return {"score": 0.0, ...}

    # Layer 2: LLM grades against rubric levels (not freeform float)
    rubric = self.world_model["categories"][category_id]["rubric"]
    llm_level = self._llm_rubric_grade(transcript, rubric)  # Returns 1-4

    # Layer 3: Combine
    final_score = (deterministic_score * 0.3) + (llm_level / 4.0 * 0.7)
    return {"score": final_score, ...}
```

### EVAL-02: Default 0.5 on grading failure inflates scores

`_grade_sandbox()` line 188: If the grading LLM call crashes, returns `{"score": 0.5}`. Over many cycles, this injects noise that biases upward (0.5 is mid-range, but many real scores should be lower).

**Fix:** Default to 0.0 on grading failure, with a flag indicating the score is unreliable:

```python
return {"score": 0.0, "quality_reason": "Grading failed — score unreliable", "grading_failed": True}
```

### EVAL-03: Task generation is random, not progressive

`_generate_task()` picks a random anchor and failure mode. There's no difficulty progression — cycle 1 and cycle 100 get tasks of the same expected difficulty.

**Suggestion:** Implement progressive difficulty based on current scores:

```python
def _generate_task(self, category_id, current_score=0.0):
    # Pick difficulty based on current performance
    if current_score < 0.3:
        difficulty = "basic"
        anchor = anchors[0]  # Start with first/simplest anchor
    elif current_score < 0.6:
        difficulty = "intermediate"
        # Pick anchors the agent hasn't mastered
    else:
        difficulty = "advanced"
        # Combine multiple anchors, add edge cases
```

### EVAL-04: Sandbox tool_terminal has no directory isolation enforcement

`tool_dispatcher.py` line 33: `tool_terminal` runs shell commands with `cwd=self.sandbox_path` but doesn't prevent `cd ..` or absolute paths in the command string. An LLM could `cd /` and access the entire filesystem.

**Suggestion:** For open-source release, either:

1. Use a proper sandbox (Docker container, chroot, or bubblewrap)
2. At minimum, block commands containing `..`, absolute paths, and dangerous operations:

```python
blocked_patterns = ["cd ..", "rm -rf /", "sudo", "curl", "wget"]
```

### EVAL-05: No eval result correlation validation

`eval_read_scores()` strips prefixes (`req-`, `eval-`) and does substring matching on IDs (line 28). This is fragile — `req-abc` and `eval-abc` would both match `abc`.

**Fix:** Store the exact `request_id` in the eval request file and match it exactly in results.

---

## 5. Adapter Layer — Multi-LLM Robustness <a name="adapter-layer"></a>

### ADAPT-01: Gemini adapter uses raw urllib, no retry logic

`adapters/providers/gemini.py` makes a single HTTP request (line 93). On transient network errors or 429 rate limits, it crashes the entire cycle.

**Suggestion:** Add retry with exponential backoff:

```python
for attempt in range(3):
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        break
    except urllib.error.HTTPError as e:
        if e.code == 429 and attempt < 2:
            time.sleep(2 ** attempt * 5)
            continue
        raise
```

### ADAPT-02: Ollama and OpenAI-compat adapters don't support tools

`ollama.py` line 37: `supports_tools = False`. `openai_compat.py` line 57: `supports_tools = False`. But the agent loop always passes tools. These adapters silently ignore them.

**Problem:** If someone configures Ollama as the evolution provider, the LLM receives no tool definitions and can't call any tools. The cycle will hit 3 empty turns and abort.

**Suggestion:** Either:

1. Add tool support to Ollama adapter (Ollama supports function calling now)
2. Have `agent_loop.py` check `adapter.supports_tools` and fail fast with a clear error
3. Add a compatibility matrix in the README

### ADAPT-03: OpenAI adapter doesn't handle streaming

All adapters inherit `stream()` from `BaseAdapter` which raises `NotImplementedError`. For future token-efficient streaming support, this should be implemented at least for OpenAI and Anthropic.

**Low priority** — not needed for evolution loop, but good for the director interface.

### ADAPT-04: No adapter-level token counting for budget management

`router_get_budget()` returns config limits, but there's no actual token tracking. The `usage` returned by adapters is logged but never accumulated.

**Suggestion:** Add a `TokenTracker` that accumulates `usage` across calls within a cycle:

```python
class TokenTracker:
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0

    def add(self, usage):
        self.input_tokens += usage.get("input_tokens", 0)
        self.output_tokens += usage.get("output_tokens", 0)
```

---

## 6. Skill-by-Skill Findings <a name="skill-by-skill-findings"></a>

### loop-orchestrator

- `loop_start.py` — Clean, no issues. Properly initializes cycle state.
- `loop_advance_stage.py` — Stage list `["REFLECT", "EVOLVE", "EVAL", "END"]` is hardcoded (line 14). Consider pulling from config for future extensibility.
- `loop_end_cycle.py` — Has bare `except: pass` (BUG-10). Otherwise correct. High-water mark auto-update logic is good.
- `loop_get_state.py` — Clean, no issues.
- **Verdict:** Solid infrastructure skill. Fix the bare except.

### meta-evolution

- `evolve_orient.py` — Core targeting logic. The priority scoring (line 103: `size_bytes / 1000.0`) is arbitrary. `related_to_weakest` never matches real skills (GAP-02). Random shuffle of candidates means non-deterministic targeting.
- `evolve_set_target.py` — Clean, writes target to session.
- `evolve_propose.py` — Line 22: silently passes if `forge_validate` is missing from registry. Should at minimum log a warning.
- `evolve_apply.py` — Calls `kernel.reload_skill()` which DOES exist (line 221 of kernel.py). Moves proposal to evolution_records. Correct.
- `evolve_rollback.py` — Delegates to `forge_rollback`. Clean.
- `evolve_create_skill.py` — Creates scaffolds with stub implementations (`return {'status': 'ok'}`). This means newly forged skills do nothing until the LLM edits them in a subsequent cycle.
- `evolve_modify_loop.py` — Logs to JSONL but doesn't execute. This is intentional (dangerous), but should be documented.
- `evolve_history.py` — Clean.
- **Suggestion:** The orient function needs a proper targeting algorithm. See NEW-02 below.

### meta-evaluation

- `review_proposal.py` — Rubber stamp problem (GAP-04). Regex JSON parsing bug (BUG-04). The review prompt itself is actually good — it checks correctness, improvement, safety, syntax, and has anti-cosmetic-change rules.
- `review_modify.py` — Just logs the modification request. Doesn't actually re-submit for review.
- `review_criteria_update.py` — Writes criteria to file. Never read by `review_proposal`. Dead feature.
- `review_history.py` — Clean, reads records.
- **Suggestion:** `review_criteria_update` should actually be loaded and used by `review_proposal`. The criteria file should be read at the start of review and injected into the review prompt.

### reflection

- `reflection_analyze_trace.py` — Good analysis logic. Correctly filters by active world model categories. Hardcoded category recommendations (GAP-05) should be made dynamic.
- `reflection_write_hypothesis.py` — Clean.
- `reflection_read_hypothesis.py` — Clean.
- **Verdict:** Strong skill. Dynamic recommendations would make it excellent.

### eval-bridge

- `eval_request.py` — Clean. Writes request JSON to shared directory.
- `eval_read_scores.py` — 5-minute polling timeout (line 30). The ID matching logic (stripping prefixes, line 28) is fragile but functional.
- `eval_check_regression.py` — Good adaptive threshold logic (5% → 3% → 2% based on cycle count). Well-designed.
- `eval_update_high_water.py` — Correct. Silently skips non-numeric scores.
- `eval_backfill.py` — Clean.
- **Verdict:** Core eval plumbing works. Add health check for eval-generator process.

### skill-forge

- `forge_snapshot.py` — Copies function files to `snapshots/{id}/functions_backup/`. Lines 10-19 have complex skill name extraction from paths that's fragile with Windows backslashes.
- `forge_apply_diff.py` — String find-and-replace with py_compile validation and auto-revert. Functional but crude. No partial-failure handling (if chunk 2 of 3 fails, chunk 1 is already applied — but the file IS reverted to original on syntax error, so this is mostly safe).
- `forge_validate.py` — Runs py_compile on target. Clean.
- `forge_test_suite.py` — Runs pytest with 60s timeout. Assumes pytest is installed (not in requirements.txt! See OSR-04).
- `forge_invoke.py` — Calls function from registry. No param validation.
- `forge_rollback.py` — Restores from snapshot. Line 20 assumes backup_dir exists without checking.
- `forge_create_skill.py` — Creates scaffold. Properly updates manifest.json and hot-loads.
- **Suggestion:** `forge_snapshot.py` should normalize paths using `pathlib.PurePosixPath` to handle Windows backslashes consistently. `forge_rollback.py` should check backup existence before attempting restore.

### memory

- `memory_page_in.py` — BUG-07 (non-existent kernel methods), BUG-08 (bare excepts). The core file-reading logic works.
- `memory_page_out.py` — BUG-01 (hardcoded relative path).
- `memory_search_sql.py` — BUG-09 (bare except). Misleading name — it's keyword grep, not SQL.
- `memory_commit_archival.py` — Clean. Writes experience entries correctly.
- **Big gap:** README claims "SQLite + Vector database" but there's no SQLite or vector search anywhere. This is just JSON file scanning.
- **Suggestion:** Either implement actual SQLite + vector search (using `sqlite3` + a simple embedding approach), or correct the README. For a self-evolving system, proper memory is critical — keyword grep won't scale past a few hundred entries.

### reasoning

- `reason_decompose.py` — BUG-03 (undefined variable). Otherwise delegates to LLM for problem decomposition. Functional when the bug is fixed.
- `reason_evaluate_options.py` — BUG-02 (wrong signature). Dead code.
- `reason_check_logic.py` — BUG-12 (complete no-op).
- `reason_generate_plan.py` — BUG-05 (greedy regex). Delegates plan generation to LLM. Has a schema defined in `tool_schemas.py`? Actually NO — `reason_generate_plan` is NOT in `tool_schemas.py`. It exists as a function file but has no schema, so it's never registered and never callable.
- **Verdict:** This skill is the weakest in the codebase. 1 of 4 functions works (decompose, with a bug). For a system that claims reasoning as a core capability, this needs significant work.
- **Suggestion:** See NEW-04 below.

### tool-use

- `tool_terminal.py` — Solid implementation. Sync + async execution, stdout/stderr capture, timeout handling. Hardcoded 120s timeout and 4000-char truncation should be configurable.
- `tool_terminal_input.py` — Clean. Sends stdin to background jobs.
- `tool_terminal_kill.py` — Clean.
- `tool_file_edit_diff.py` — Find-and-replace with py_compile validation and auto-revert. Good safety.
- `tool_apply_patch.py` — BUG-06 (missing CWD). Otherwise functional git apply wrapper.
- **Verdict:** Best-implemented skill in the codebase. Production quality.

### web-research

- `research_search_engine.py` — Scrapes DuckDuckGo HTML with custom HTMLParser. Fragile — class names and HTML structure can change anytime. Line 52 has inconsistent indentation (extra leading space).
- `research_browse.py` — Basic URL fetcher with 10KB truncation. No error handling for non-200 responses.
- `research_archive_source.py` — Saves content to memory. 5KB truncation.
- **Suggestion:** Use DuckDuckGo's API (`duckduckgo_search` package) instead of scraping HTML. Add to requirements.txt. Or use a search API that's designed for programmatic access.

### context-orchestration

- `context_load.py` — Assembles context from multiple sources. Silent JSON parsing failures (logged but continue). Otherwise correct.
- `context_get_manifest.py` — Clean.
- **Verdict:** Solid.

### mode-controller

- `mode_get.py` — Clean.
- `mode_set.py` — Clean. Validates mode values.
- **Verdict:** Simple and correct.

### skill-router

- `router_get_tools.py` — Line 14: assumes functions have `__doc__`, can be `None`. Should default to empty string.
- `router_get_budget.py` — Clean.
- `router_manifest.py` — Clean.
- **Verdict:** Fine.

### eval_util

- `generate_evaluation_artifact.py` — Single utility function. Clean.
- **Verdict:** Minimal but correct.

### director-interface

- `interface.py` — Rich terminal UI with prompt_toolkit. Professional implementation. Command parsing, log streaming, status display.
- **Verdict:** Well-built. This is the best user-facing piece.

---

## 7. New Features for World-Class Self-Evolution <a name="new-features"></a>

### NEW-01: Ship a BOROS.md with the repo

This is the LLM's identity and operating manual. Without it, the evolution loop runs blind. Create `BOROS.md` with:

- Identity: "You are Boros, an autonomous self-evolving AI substrate"
- Operating principles: Skill-first modification, escalation ladder
- Constraints: Don't modify kernel/adapters/infrastructure skills
- How to read scores and world model
- How to write SKILL.md modifications
- Anti-patterns: cosmetic changes, infinite rewrites, targeting infrastructure

### NEW-02: Intelligent targeting algorithm (replace random selection)

Replace the random candidate selection in `evolve_orient.py` with a proper strategy:

**Multi-Armed Bandit approach:**

```python
# Track success rate per skill target
# UCB1 score = average_improvement + sqrt(2 * ln(total_cycles) / times_targeted)
# Prefer skills that have either shown improvement or haven't been tried
```

**Or at minimum, a heuristic ranking:**

1. Skills directly mapped to the weakest category (fix GAP-02 first)
2. Skills with SKILL.md files (semantic improvement possible)
3. Skills with larger function files (more room for improvement)
4. Skills NOT targeted in the last 3 cycles (diversity)
5. Skills where previous evolution was rejected (revisit with new approach)

### NEW-03: Implement deterministic eval scoring layers

See EVAL-01 for details. The key insight: LLM grading is unreliable for tracking improvement over time. Add deterministic checks:

1. **Did the agent produce output files?** (already exists)
2. **Does the output compile/run?** (new)
3. **Does the output contain structured elements matching the rubric?** (new)
4. **LLM grades against discrete rubric levels, not freeform float** (new)

### NEW-04: Rebuild the reasoning skill

The reasoning skill should be the showcase capability. Current state: 1 working function out of 4.

**Proposed implementation:**

- `reason_decompose` — Fix the bug, keep LLM delegation but add structured output parsing
- `reason_evaluate_options` — Fix signature, implement multi-criteria scoring with weighted evaluation
- `reason_check_logic` — Implement by calling the LLM with a specific logic-checking prompt (like `reason_decompose` does), checking for contradictions, unsupported assumptions, circular reasoning
- `reason_generate_plan` — Add schema to `tool_schemas.py`, fix the JSON parsing

### NEW-05: Implement real memory (SQLite + vector search)

Replace keyword-grep memory with actual structured storage:

```python
import sqlite3
import json
import hashlib

class MemoryStore:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                type TEXT,
                content TEXT,
                tags TEXT,
                timestamp TEXT,
                embedding_hash TEXT
            )
        """)

    def search(self, query, limit=10):
        # Full-text search using SQLite FTS5
        ...

    def store(self, entry_type, content, tags):
        ...
```

For vector search without heavy dependencies, use a simple TF-IDF approach with `sklearn` or even just cosine similarity on bag-of-words. Don't need full embeddings for this use case.

### NEW-06: Add a unified launcher script

```python
# run.py
import subprocess, sys, signal, time

def main():
    # Start eval-generator in background
    eval_proc = subprocess.Popen(
        [sys.executable, "eval-generator/eval_generator.py"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    # Wait for eval-generator to be ready
    ready_file = "eval-generator/shared/.ready"
    for _ in range(30):
        if os.path.exists(ready_file):
            break
        time.sleep(1)

    # Start kernel
    from kernel import BorosKernel
    kernel = BorosKernel()
    # ... launch director interface

    # Cleanup on exit
    signal.signal(signal.SIGTERM, lambda *_: eval_proc.terminate())
```

### NEW-07: Add evolution metrics dashboard

Track and display:

- Score history graph (per category over cycles)
- Evolution success rate (proposals approved vs rejected)
- Skill mutation frequency heatmap
- Time per cycle
- Token usage per cycle
- High-water mark progression

Could be a simple terminal-based display in the director interface, or write to an HTML file that can be opened in a browser.

### NEW-08: Add multi-model review board

The README mentions a review board with "GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro" but the actual implementation uses a single LLM. Implement actual multi-model review:

```python
def review_proposal_multi(params, kernel):
    verdicts = []
    for llm in [kernel.meta_eval_llm, kernel.evolution_llm]:  # Or more
        verdict = _single_review(params, llm)
        verdicts.append(verdict)

    # Majority vote
    apply_count = sum(1 for v in verdicts if v["verdict"] == "apply")
    final = "apply" if apply_count > len(verdicts) / 2 else "reject"
```

### NEW-09: Add snapshot diffing and evolution audit trail

When a proposal is applied, store the actual diff (not just the proposal metadata). This enables:

- `evolve_history` to show what actually changed (before/after)
- Detecting patterns in successful vs failed evolutions
- Rolling back to any previous state, not just the last snapshot

### NEW-10: Implement SKILL.md-aware evolution

The escalation ladder says "modify SKILL.md first" but there's no tooling specifically for this. Add:

1. A `forge_read_skill_md(skill_name)` tool that returns the parsed SKILL.md
2. A `forge_edit_skill_md(skill_name, section, new_content)` tool that modifies specific sections
3. Validation that SKILL.md changes are well-formed markdown

This makes semantic evolution (the preferred approach) first-class instead of relying on generic file editing.

### NEW-11: Cross-platform path handling

The codebase is Windows-first (`type`, `dir`, backslashes in `cycle_prompt.md`). For open-source, it needs to work on Linux/macOS too.

**Suggestion:**

- Replace all hardcoded `type`/`dir` references in `cycle_prompt.md` with platform-aware instructions
- Use `pathlib.Path` consistently instead of `os.path.join` with string slashes
- In `build_system_prompt()`, detect the OS and inject appropriate commands:

```python
import platform
if platform.system() == "Windows":
    parts.append("Use `type` to read files, `dir` to list. Backslash paths.")
else:
    parts.append("Use `cat` to read files, `ls` to list. Forward slash paths.")
```

---

## 8. Open-Source Readiness <a name="open-source-readiness"></a>

### OSR-01: Add a LICENSE file

No license file exists. For open-source, add MIT, Apache 2.0, or your preferred license.

### OSR-02: Add `.env.template` documentation

The template exists but the README only mentions `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`. The actual config uses Gemini as default. Document all possible keys:

```
ANTHROPIC_API_KEY=     # Required if using Anthropic provider
GEMINI_API_KEY=        # Required if using Gemini provider (default)
OPENAI_API_KEY=        # Required if using OpenAI provider
TOGETHER_API_KEY=      # Optional, for Together.xyz models
```

### OSR-03: Fix README accuracy

- "SQLite + Vector database" → doesn't exist (keyword grep only)
- "Associative Memory Engine" → just JSON file reading
- Quick start says to edit `.env` with `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` but default config uses Gemini
- No mention of starting the eval-generator
- The "Proof of Evolution" case study should be marked as illustrative/example, or replaced with real data once available

### OSR-04: Add missing dependencies to requirements.txt

```
pytest>=7.0.0          # Used by forge_test_suite but not listed
duckduckgo-search>=3.0 # If implementing proper web search (NEW suggestion)
```

### OSR-05: Add a `setup.py` or `pyproject.toml`

For proper Python packaging:

```toml
[project]
name = "boros"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.39.0",
    "openai>=1.50.0",
    "google-generativeai>=0.8.0",
    "prompt_toolkit>=3.0.0",
    "rich>=13.0.0",
    "python-dotenv>=1.0.0",
]
```

### OSR-06: Add contribution guidelines

For open-source contributors:

- How to add a new world model category
- How to add a new skill manually
- How to add a new LLM adapter
- How to run the system in test mode
- Architecture decision records

### OSR-07: Add a world model template/examples

Ship 2-3 example world models:

- `world_model.examples/coding.json` — for code generation capability
- `world_model.examples/reasoning.json` — the current default
- `world_model.examples/research.json` — for web research capability

Each with proper `related_skills` that map to actual skill directories.

### OSR-08: Docker support

A `Dockerfile` and `docker-compose.yml` that:

- Sets up Python environment
- Runs both kernel and eval-generator
- Mounts `.env` for API keys
- Exposes the director terminal

This solves the sandbox safety concern (EVAL-04) and makes deployment trivial.

---

## 9. Suggested Execution Order <a name="execution-order"></a>

### Phase 1: Make it work (fix crashes)

1. Fix all 12 critical bugs (BUG-01 through BUG-12)
2. Fix world model `related_skills` mapping (GAP-02)
3. Create BOROS.md (NEW-01)
4. Add unified launcher (NEW-06)
5. Fix meta-evaluation default to reject (GAP-04)

### Phase 2: Make it reliable (trustworthy evolution)

6. Add deterministic eval scoring layers (NEW-03)
7. Fix default 0.5 grading to 0.0 (EVAL-02)
8. Remove hardcoded category logic in reflection (GAP-05)
9. Add crash recovery in loop_start (GAP-07)
10. Add adapter retry logic (ADAPT-01)

### Phase 3: Make it good (world-class features)

11. Rebuild reasoning skill (NEW-04)
12. Implement intelligent targeting (NEW-02)
13. Implement real memory with SQLite (NEW-05)
14. Add SKILL.md-aware evolution tools (NEW-10)
15. Cross-platform support (NEW-11)
16. Multi-model review board (NEW-08)

### Phase 4: Make it open-source ready

17. LICENSE, setup.py, contribution docs (OSR-01 through OSR-06)
18. Fix README accuracy (OSR-03)
19. Docker support (OSR-08)
20. World model templates (OSR-07)
21. Evolution metrics dashboard (NEW-07)

---

_Audit completed: every Python file in the repository was read and analyzed. All findings reference specific files and line numbers._
