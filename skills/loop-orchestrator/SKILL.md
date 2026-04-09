# Loop Orchestrator

You manage stage transitions, cycle counting, and session lifecycle. You are the backbone of the REFLECT → EVOLVE → EVAL cycle.

---

## Your Role

You coordinate. You do not reason, evaluate code, or make evolution decisions — that is for Reflection, Meta-Evolution, and Meta-Evaluation. You:

- Start each cycle and initialise state
- Enforce gates between stages
- End cycles, archive hypothesis outcomes, clear session
- Track crash recovery

---

## Functions

### loop_start()

Called at the start of every evolution cycle by the agent loop.

What it does:
1. Detects crash recovery — if `session/loop_state.json` shows a non-null stage, a crash occurred mid-cycle. Attempts auto-rollback using `snapshot_id` from `session/evolution_target.json`.
2. Reads cycle number from `session/current_cycle.json`, increments it.
3. Writes new `session/loop_state.json` with stage=REFLECT.
4. Calls `context_load()` to populate `session/context_manifest.json`.

```
→ {"status": "ok", "state": {...}, "recovered_from_crash": bool}
```

### loop_advance_stage()

Advances from the current stage to the next in the sequence: `REFLECT → EVOLVE → EVAL → END`.

**Hard gate — REFLECT → EVOLVE**: checks that `session/hypothesis.json` exists. If missing, returns an error — do not proceed to EVOLVE without a hypothesis. Call `reflection_write_hypothesis` first.

```
params: {}   ← reads current stage from loop_state.json automatically
→ {"status": "ok", "previous_stage": str, "next_stage": str, "state": {...}}
→ {"status": "error", "message": "Cannot advance to EVOLVE without a hypothesis..."}
```

### loop_end_cycle()

Ends the current cycle. Must be called after EVAL is complete.

What it does, in order:
1. **Archives the hypothesis** — reads `session/hypothesis.json`, computes score delta by comparing the last two `score_history.jsonl` entries, writes `memory/evolution_records/hyp-cycle{N}.json` with outcome (`improved`/`regressed`/`neutral`/`baseline`), then deletes `session/hypothesis.json`.
2. **Updates high-water marks** — calls `eval_update_high_water` with the latest scores.
3. **Checks milestone advancement** — calls `eval_check_milestone` to see if any category should advance in `world_model.json`.
4. **Clears session** — removes all files from `session/` except `loop_state.json`, `current_cycle.json`, and `evolution_target.json`. `hypothesis.json` is deleted (archived above, not kept).
5. **Logs** — appends cycle end line to `logs/cycles.log`.

```
→ {
    "status": "ok",
    "cycle": int,
    "message": str,
    "high_water_updated": {...},
    "hypothesis_archived": bool
  }
```

### loop_get_state()

Returns the current `session/loop_state.json`.

```
→ {"status": "ok", ...state dict...}
```

---

## Stage Sequence

```
REFLECT → EVOLVE → EVAL → (loop_end_cycle) → next cycle
```

**REFLECT**: Analyze scores and past hypothesis outcomes. Write a hypothesis. Call `loop_advance_stage`.
**EVOLVE**: Load hypothesis, modify a skill, get review, apply if approved. Call `loop_advance_stage`.
**EVAL**: Request evaluation, read scores, check regression (auto-rollbacks if needed), update high-water marks. Call `loop_end_cycle`.

---

## Hypothesis Lifecycle

- Written by `reflection_write_hypothesis` → `session/hypothesis.json`
- Required by `loop_advance_stage` (hard gate from REFLECT)
- Persists through EVOLVE and EVAL within the same cycle
- **Archived by `loop_end_cycle`** to `memory/evolution_records/hyp-cycle{N}.json` with score delta
- **Deleted from session** at cycle end — never persists across cycles

This means: at the start of REFLECT, there is NO active hypothesis from the previous cycle. The LLM sees archived outcomes (via the system prompt block) but must write a fresh hypothesis.

---

## Crash Recovery

If `loop_state.json` shows a non-null stage when `loop_start` is called, a crash is detected. `loop_start` attempts to rollback by reading `snapshot_id` from `session/evolution_target.json` (written by `forge_snapshot`). If no snapshot_id is present, no rollback occurs — evolution continues from the next cycle.

---

## State Files

| File | Purpose |
|------|---------|
| `session/loop_state.json` | Current cycle, stage, mode, started_at, total_cycles_completed |
| `session/current_cycle.json` | Authoritative cycle number |
| `session/evolution_target.json` | Current target skill, category, approach, snapshot_id |

---

## Rules

1. **Never skip `loop_end_cycle`** — it archives the hypothesis and clears session. If the LLM ends without calling it, `agent_loop.py`'s safety net calls it automatically.
2. **Hypothesis gate is enforced in code** — `loop_advance_stage` returns an error if `session/hypothesis.json` is missing when advancing from REFLECT.
3. **`hypothesis.json` is not kept across cycles** — it is archived then deleted by `loop_end_cycle`. Each cycle starts fresh.
4. **Cycle counter lives in `session/current_cycle.json`** — do not infer it from evolution record counts.

---
