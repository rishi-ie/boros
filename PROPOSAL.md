# Boros Evolution Overhaul — Revised Proposal

Based on a complete read of every file in the system: kernel.py, agent_loop.py, all 15 skills (SKILL.md + every function), eval-generator, cycle_prompt.md, BOROS.md, config.json, world_model.json, tool_schemas.py, and the actual state on disk.

---

## DIAGNOSIS: Why Boros Doesn't Actually Evolve

After 5 cycles, scores went: `web_search 0.5 → 0.167 → 0.333`. Reasoning hit 0.645 once and was never re-tested. The system is running but regressing. Here's why, ranked by severity:

**1. The LLM has amnesia.** `session/hypothesis.json` is in the `keep` set in `loop_end_cycle.py`, so it persists across cycles. The LLM reads the stale hypothesis, thinks it's current, and writes the same one. `memory/experiences/` is empty because `context_load.py` reads `experiences.jsonl` (doesn't exist) while `memory_commit_archival.py` writes individual `exp-*.json` files. Block 4 of the system prompt is always empty.

**2. The LLM is blind to its own scores.** `agent_loop.py` (build_system_prompt) reads `evals/scores/*.json` to inject a "Recent Evaluation Scores" block. That directory is empty — nothing ever writes there. Scores go to `eval-generator/shared/results/` and `memory/score_history.jsonl` instead. The score_history path works separately, but the detailed per-eval breakdown (scoring_breakdown, quality_reason) is never seen by the LLM.

**3. SKILL.md says one thing, code does another.** This is pervasive and devastating — the LLM reads SKILL.md docs that promise behaviors the code doesn't implement:
- `eval_check_regression` SKILL.md says "triggers automatic rollback" — code just returns a recommendation string
- `eval_request` SKILL.md says it "polls for results" — code just writes a request file and returns immediately
- `loop_advance_stage` SKILL.md says "hard hypothesis gate" — code advances unconditionally
- `evolve_propose` SKILL.md says "hypothesis_id required" — code accepts proposals without one
- `review_criteria_update` writes criteria that `review_proposal` never reads (criteria are hardcoded in the prompt)
- `context_load` SKILL.md promises formatted `=== SECTION ===` blocks and "Associative Whisper" semantic search — code returns a raw dict

**4. Crash recovery is silently broken.** `loop_start.py` tries to auto-rollback on crash by reading `snapshot_id` from `session/evolution_target.json`. But `evolve_set_target.py` never writes a `snapshot_id` field there (only writes `target_skill`, `category`, `approach`, `timestamp`). The auto-rollback always silently does nothing.

**5. The "modify" verdict is a dead end.** `review_proposal` can return "apply", "reject", or "modify". On "modify", it writes a record to `memory/evolution_records/modify-{id}.json` and auto-rollbacks. But nothing reads modify records or processes them. The LLM sees "modify" and has no structured way to act on it — functionally identical to "reject".

**6. Web search is broken at the HTTP level.** `DDGParser` in `research_search_engine.py` was rewritten by Boros itself during cycle 3 to use class names (`result__title`, `result__snippet` on `h2`/`div` tags) that don't match DuckDuckGo's actual HTML. Every search returns `[]`. Score dropped from 0.5 to 0.167.

**7. `eval_backfill` corrupts score_history.jsonl.** It writes bare `{"reasoning": 0.5}` dicts instead of full entries with `eval_id`, `timestamp`, `cycle`. This breaks the dedup logic in `eval_read_scores` and any code that expects those fields.

**8. World model sync only at boot.** `kernel._sync_world_model_state()` syncs `evals/categories.json` and `high_water_marks.json` from `world_model.json`, but only runs once in `__init__`. Add a new category mid-run and `eval_request` won't know about it.

**9. No difficulty progression.** `difficulty_level` is hardcoded to 5 in `eval_generator.py` line 518. The eval never gets harder or easier.

**10. Outcome scoring is noise.** The string "successfully" anywhere in the transcript (including "successfully rolled back an error") awards +0.25. Any `"Error:"` substring anywhere (including a recovered tool error) nukes both scores to 0.0.

---

## THE CHANGES

### Phase 1: Make the loop not blind (P0 — do these first)

These fix the "Boros can't see or remember anything" problem. Without these, nothing else matters.

#### 1.1 Fix the dead `evals/scores/` path

**File:** `skills/eval-bridge/functions/eval_read_scores.py`

After reading a result from `eval-generator/shared/results/`, also write a copy to `evals/scores/{eval_id}.json`. This is the simplest fix — `agent_loop.py` already reads from there correctly.

```python
# After appending to score_history.jsonl, also write to evals/scores/
import shutil
evals_scores_dir = kernel.boros_root / "evals" / "scores"
evals_scores_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(result_file, evals_scores_dir / result_file.name)
```

#### 1.2 Fix the experiences path mismatch

**File:** `skills/context-orchestration/functions/context_load.py`

`context_load` reads `memory/experiences/experiences.jsonl` (doesn't exist). `memory_commit_archival` writes individual `memory/experiences/exp-*.json` files.

**Change:** Replace the experiences.jsonl read with a glob of `memory/experiences/exp-*.json`, sorted by mtime descending, take last 5:

```python
import glob
exp_files = sorted(
    glob.glob(str(memory_dir / "experiences" / "exp-*.json")),
    key=os.path.getmtime, reverse=True
)[:5]
experiences = [json.loads(Path(f).read_text()) for f in exp_files]
```

#### 1.3 Archive hypothesis outcomes at cycle end

**File:** `skills/loop-orchestrator/functions/loop_end_cycle.py`

Currently `hypothesis.json` is in the `keep` set and persists forever. The LLM re-reads the same stale hypothesis every cycle.

**Changes:**
1. Remove `"hypothesis.json"` from the `keep` set
2. Before clearing session, read `session/hypothesis.json`, compute the score delta by comparing pre-cycle and post-cycle scores from `score_history.jsonl`, and write to `memory/evolution_records/hyp-{cycle}.json`:
```json
{
  "id": "hyp-xxx",
  "cycle": 4,
  "target_skill": "web-research",
  "rationale": "...",
  "expected_improvement": "...",
  "actual_outcome": "regressed",
  "score_before": {"web_search": 0.5},
  "score_after": {"web_search": 0.167},
  "timestamp": "..."
}
```
3. Delete `session/hypothesis.json` after archiving

#### 1.4 Inject past hypothesis outcomes into system prompt

**File:** `agent_loop.py` — `build_system_prompt()`

Add a new block (after the score_history block) that reads `memory/evolution_records/hyp-*.json`, formats the last 10 as a concise list, and injects:

```
## Previous Evolution Attempts (DO NOT REPEAT FAILED APPROACHES)
- Cycle 2: web-research / SKILL.md "Your Role" edit → REGRESSED (0.5 → 0.167). Don't edit SKILL.md text without code changes.
- Cycle 3: web-research / DDGParser rewrite → REGRESSED (0.5 → 0.167). HTML class names were wrong.
- Cycle 4: web-research / SKILL.md 5-step process → NEUTRAL (0.167 → 0.333). Cosmetic.
```

This is the single highest-leverage change. The LLM literally cannot repeat a failed approach if the failures are in its system prompt.

---

### Phase 2: Make the loop not broken (P1 — fix structural bugs)

These fix cases where the code doesn't do what it claims.

#### 2.1 Fix crash recovery — write snapshot_id to evolution_target

**File:** `skills/meta-evolution/functions/evolve_set_target.py`

Currently writes `{target_skill, category, approach, timestamp}`. `loop_start.py` reads `snapshot_id` from this file for crash recovery, but it's never there.

**Change:** Also accept and write `snapshot_id` to `evolution_target.json`. Then update `cycle_prompt.md` to tell the LLM to call `evolve_set_target` AFTER `forge_snapshot` so the snapshot_id is available.

Alternatively (simpler): have `forge_snapshot` write `snapshot_id` into `session/evolution_target.json` directly if the file exists.

#### 2.2 Auto-rollback on regression

**File:** `skills/eval-bridge/functions/eval_check_regression.py`

Currently returns text: `"ROLLBACK recommended"`. The LLM ignores it under tool budget pressure at the end of cycles.

**Change:** When regression > threshold AND `session/evolution_target.json` has a `snapshot_id`:
1. Call `kernel.registry['evolve_rollback']` with the snapshot_id and skill_name
2. Log the auto-rollback to `memory/evolution_records/rollback-{cycle}.json`
3. Return `{"status": "ok", "action": "auto_rolled_back", "reason": "..."}`

This matches what SKILL.md already promises. Also implement the adaptive threshold from SKILL.md (cycles 1-10: 0.05, 11-30: 0.03, 31+: 0.02) by reading cycle number from `session/current_cycle.json`.

#### 2.3 Add hypothesis gate to loop_advance_stage

**File:** `skills/loop-orchestrator/functions/loop_advance_stage.py`

SKILL.md says REFLECT→EVOLVE requires a hypothesis. Code advances unconditionally.

**Change:** When advancing from REFLECT to EVOLVE, check that `session/hypothesis.json` exists. If not, return error: `"Cannot advance to EVOLVE without a hypothesis. Call reflection_write_hypothesis first."`

#### 2.4 Fix the "modify" verdict dead end

**File:** `skills/meta-evaluation/functions/review_proposal.py`

When verdict is "modify", the review board provides specific feedback (`reason` field). Currently this is written to a file nobody reads.

**Change:** On "modify" verdict, instead of auto-rollback, write the modification feedback into `session/review_feedback.json`. The LLM can then read it and make the requested changes before re-proposing. Update `cycle_prompt.md` EVOLVE stage to say: "If review returns 'modify', read the feedback from `session/review_feedback.json`, make the changes, and re-propose."

#### 2.5 World model live-reload every cycle

**File:** `agent_loop.py` — `run_evolution_cycle()`

Add `self.kernel._sync_world_model_state()` at the top, before `build_system_prompt()`. The method is already idempotent and only writes on change.

#### 2.6 Fix eval_backfill format corruption

**File:** `skills/eval-bridge/functions/eval_backfill.py`

Currently writes bare score dicts `{"reasoning": 0.5}` to `score_history.jsonl`. Every other writer puts full entries with `eval_id`, `timestamp`, `cycle`.

**Change:** Write full entries matching the format used by `eval_read_scores`:
```json
{"eval_id": "eval-xxx", "cycle": 3, "timestamp": "...", "scores": {"reasoning": 0.5}, "composite": 0.5}
```

---

### Phase 3: Make the eval system a real benchmark (P2)

These make the eval-generator produce meaningful, progressively harder tests.

#### 3.1 Fix web search infrastructure

**File:** `skills/web-research/functions/research_search_engine.py`

The DDGParser uses wrong HTML class names after Boros's own failed evolution attempt broke it. Every search returns `[]`.

**Fix:** Replace the brittle HTML parser with a robust approach. Options:
- Use DuckDuckGo's `lite` endpoint which has simpler HTML
- Use the `duckduckgo-search` Python package if available
- Fix the class names to match DDG's actual current HTML structure (inspect the page)
- Simplest: use a different search API entirely (Brave, SearXNG)

This is infrastructure, not a skill — it must be fixed manually, not by evolution.

#### 3.2 Fix outcome_score false positives/negatives

**File:** `eval-generator/eval_generator.py` — scoring section

Two problems:
- `"Error:"` anywhere in transcript → both scores = 0.0 (too aggressive — recoverable tool errors kill the whole eval)
- `"successfully"` anywhere → +0.25 (too permissive — error recovery messages game the score)

**Change:**
- Only hard-fail on `"Error:"` if it appears in the LAST tool result (meaning the agent gave up on an error), not in any intermediate result
- Replace keyword matching with a check: did the agent produce a non-trivial output file AND was the final tool result status "ok"?

#### 3.3 Add milestone-based difficulty to world_model.json

**File:** `world_model.json` — restructure

Add a `milestones` array to each category. Each milestone has its own `anchors`, `rubric`, `failure_modes`, `task_template`, and `difficulty`. The eval-generator reads the current milestone's settings instead of randomly picking from flat lists.

```json
{
  "version": 2,
  "categories": {
    "reasoning": {
      "weight": 2.5,
      "current_milestone": 0,
      "milestones": [
        {
          "level": 1,
          "name": "Basic decomposition",
          "difficulty": 3,
          "unlock_score": 0.6,
          "unlock_consecutive": 2,
          "anchors": ["..."],
          "rubric": {"level_1": "...", "level_4": "..."},
          "failure_modes": ["..."],
          "task_template": "...",
          "execution_pattern": {"...": "..."}
        }
      ]
    }
  }
}
```

**Key design:** `current_milestone` is an index into `milestones[]`. It advances when `unlock_score` is sustained for `unlock_consecutive` evals. For backward compat, if `milestones` is absent, fall back to the flat fields (anchors, rubric, etc.) — this means existing world models still work.

#### 3.4 Eval-generator reads milestones

**File:** `eval-generator/eval_generator.py`

In `_generate_task()`, check if the category has `milestones`. If yes, use `milestones[current_milestone]` for anchors/rubric/failure_modes/task_template/execution_pattern. If no, use the existing flat fields.

Replace hardcoded `"difficulty_level": 5` with the milestone's `difficulty` value.

#### 3.5 Milestone advancement

**File:** New — `skills/eval-bridge/functions/eval_check_milestone.py`

After each eval:
1. For each scored category, read `current_milestone` from world_model.json
2. If score >= `unlock_score`, increment a counter in `skills/eval-bridge/state/milestone_progress.json`
3. If counter >= `unlock_consecutive`, advance `current_milestone` in world_model.json
4. If score < `unlock_score`, reset counter to 0
5. Log advancement to `memory/evolution_records/milestone-{cat}-{level}.json`

Call this from `loop_end_cycle` after updating high-water marks.

Register in tool_schemas.py and manifest.json.

---

### Phase 4: Robustness (P3 — nice to have)

#### 4.1 Kernel isolation in eval-generator

**File:** `eval-generator/eval_generator.py`

Currently one `BorosKernel` shared across concurrent category evals via ThreadPoolExecutor.

**Fix:** Instantiate a fresh kernel per `_run_single_task()` call. The kernel is lightweight (config + manifest + registry). This prevents state leakage between concurrent eval tasks.

#### 4.2 Unify score sources of truth

Designate `memory/score_history.jsonl` as authoritative. `evals/scores/` is a read-optimized copy for prompt injection. `eval-generator/shared/results/` is transient (delete after processing).

#### 4.3 Fix the status variable clobbering in agent_loop.py

`agent_loop.py` line ~324: `status = self._describe_tool_call(name, inp)` overwrites the outer `status` variable that tracks cycle outcome ("completed"/"timeout"/"error"). The finally block then logs the description string instead of the actual status.

**Fix:** Rename to `description = self._describe_tool_call(name, inp)`.

#### 4.4 Ensure SKILL.md docs match code everywhere

Audit pass: for every skill, ensure SKILL.md accurately describes what the code does. The LLM reads SKILL.md to understand tool behavior. When docs lie, the LLM makes wrong assumptions. Key files to fix:
- `eval-bridge/SKILL.md` — remove claims about auto-rollback, polling, adaptive thresholds, snapshots, git tags (unless we implement them in Phase 2)
- `context-orchestration/SKILL.md` — remove Associative Whisper, formatted string claims
- `loop-orchestrator/SKILL.md` — update to reflect actual stage list and hypothesis gate behavior
- `meta-evaluation/SKILL.md` — remove review_criteria_update claims (it has no effect)

---

## WILL THIS WORK FOR ANY WORLD MODEL?

**Yes, with the milestone design.** Here's why:

The pipeline from world_model.json → eval is already dynamic:
- `eval_generator.py` reads categories from world_model.json on every request (hot-reload)
- `reflection_analyze_trace` reads categories from world_model.json per invocation
- `evolve_orient` reads `related_skills` from world_model.json per invocation
- `agent_loop.py` reads world_model.json per cycle for prompt injection

So if you add a new category `"code_generation"` with `related_skills: ["tool-use"]`, the system will:
1. Generate eval tasks for it (using its anchors/rubric/task_template)
2. Score Boros on it
3. Identify it as weakest if it scores lowest
4. Target `tool-use` skill for evolution
5. Evolve, re-test, commit or rollback

**What's needed for "any world model":**

1. **Phase 2.5 (world model live-reload)** — so new categories are picked up without restart
2. **Phase 3.3 (milestone fallback)** — so flat-format world models (no milestones) still work
3. **Each category must have `related_skills` pointing to skills that actually exist** — if you add a category targeting a skill that doesn't exist, `evolve_orient` will find no candidates. The fix: have `evolve_orient` check if related_skills exist and warn clearly if not (currently it silently returns empty candidates).
4. **Each category needs a meaningful `task_template`** — this is the prompt injected into the eval sandbox agent. A bad template produces untestable tasks. The eval-generator LLM (Gemini) generates concrete tasks FROM the template, so the template quality is the ceiling on eval quality.
5. **The `execution_pattern` must reference tools the eval sandbox actually has** — the eval sandbox blocks `identity_`, `loop_`, `evolve_`, `eval_`, `forge_`, `mission_`, `comm_`, `router_` prefixes. If your category needs tools that are blocked, the agent can't use them.

**What WON'T work without more changes:**

- Categories requiring external APIs (e.g., "database_management") — needs new skills AND tools registered first
- Categories where the eval can't be sandbox-verified (e.g., "conversation_quality") — the eval-generator checks for output files and tool calls, not subjective quality
- More than ~5 categories simultaneously — the system prompt would bloat (each category adds ~200 tokens of anchors/rubric), and eval time scales linearly (3 tasks x N categories x ~90s each)

---

## IMPLEMENTATION ORDER

```
Day 1: Stop the bleeding
  [1.1] Fix evals/scores/ dead path (eval_read_scores.py — 5 lines)
  [1.2] Fix experiences path mismatch (context_load.py — 10 lines)  
  [1.3] Archive hypotheses at cycle end (loop_end_cycle.py — 30 lines)
  [1.4] Inject past hypotheses into prompt (agent_loop.py — 20 lines)
  [3.1] Fix web search (research_search_engine.py — rewrite DDGParser or swap backend)

Day 2: Structural integrity  
  [2.1] Fix crash recovery snapshot_id (evolve_set_target.py — 3 lines)
  [2.2] Auto-rollback on regression (eval_check_regression.py — 20 lines)
  [2.3] Hypothesis gate (loop_advance_stage.py — 5 lines)
  [2.5] World model live-reload (agent_loop.py — 1 line)
  [2.6] Fix eval_backfill format (eval_backfill.py — 10 lines)
  [4.3] Fix status variable clobbering (agent_loop.py — 1 line)

Day 3: Better benchmarks
  [3.2] Fix outcome_score (eval_generator.py — 15 lines)
  [3.3] Milestone world model schema (world_model.json — restructure)
  [3.4] Eval-generator reads milestones (eval_generator.py — 20 lines)
  [3.5] Milestone advancement (new file + registration — 40 lines)
  [2.4] Fix modify verdict (review_proposal.py — 10 lines)

Day 4: Polish
  [4.1] Kernel isolation (eval_generator.py — 5 lines)
  [4.4] SKILL.md audit (multiple files — text only)
  [4.2] Score source cleanup (eval_read_scores.py — 5 lines)
```

**After Day 1 alone**, the system should stop repeating hypotheses and stop being blind to scores. That's enough to see real evolution attempts — even if some are still clumsy.

**After Day 2**, the system is structurally sound: crashes recover, regressions auto-rollback, stages enforce gates.

**After Day 3**, the benchmark adapts to Boros's level, and you can swap in any world model with milestones and watch it climb.
