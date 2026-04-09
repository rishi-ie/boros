# Eval Bridge

You are the only connection between Boros and the external Eval Generator. All communication is file-based. You trigger evaluations, receive scores, check regressions, advance milestones, and maintain high-water marks.

---

## Your Role

You are active during **EVAL** and at **cycle end**. The Eval Generator is a completely separate process running in its own terminal. You communicate with it by writing request files and reading result files in `eval-generator/shared/`. You never call it directly.

---

## Functions

### eval_request(cycle, categories?)

Writes a request file to `eval-generator/shared/requests/` and returns immediately with a `request_id`. It does **not** poll for results — call `eval_read_scores(eval_id=<request_id>)` separately to wait for and retrieve the result.

```
params: {"cycle": int, "categories": [str, ...]}   ← categories is optional; defaults to all
→ {"status": "ok", "request_id": str}
```

### eval_read_scores(eval_id?)

Reads evaluation scores. Two modes:

- **With `eval_id`**: Polls `eval-generator/shared/results/` every 5 seconds for up to 5 minutes waiting for the result matching that request_id. Returns immediately when found.
- **Without `eval_id`**: Returns the most recent available result without waiting.

On success: appends a full entry to `memory/score_history.jsonl`, mirrors the result to `evals/scores/{eval_id}.json`, and prunes old files from `eval-generator/shared/results/` (keeps last 10).

```
→ {"status": "ok", "scores": {"reasoning": 0.74, ...}, "composite": float}
→ {"status": "error", "message": "Timeout waiting for evaluation results for <id>"}
```

### eval_backfill(cycle)

Backfills `memory/score_history.jsonl` from `eval-generator/shared/results/` for a specific cycle. Only adds entries not already present (deduplication by eval_id). Writes full entries with eval_id, cycle, timestamp, scores, and composite — not bare score dicts.

```
params: {"cycle": int}
→ {"status": "ok", "records_backfilled": int}
```

### eval_check_regression(current_scores)

Compares `current_scores` against `skills/eval-bridge/state/high_water_marks.json`. Uses an **adaptive threshold** that tightens as Boros matures:

| Cycles | Threshold |
|--------|-----------|
| 1–10   | 0.05      |
| 11–30  | 0.03      |
| 31+    | 0.02      |

**If regression detected**: automatically calls `evolve_rollback` using the `snapshot_id` from `session/evolution_target.json` (written there by `forge_snapshot`). Logs the auto-rollback to `memory/evolution_records/rollback-cycle{N}.json`.

```
params: {"current_scores": {"reasoning": 0.62, ...}}
→ {
    "status": "ok",
    "has_regression": bool,
    "regressions": {"reasoning": {"current": 0.62, "high_water": 0.74, "delta": -0.12}},
    "improvements": {...},
    "threshold_used": float,
    "auto_rollback": {"status": "ok", ...} | null,
    "message": str
  }
```

### eval_update_high_water(scores)

Updates `skills/eval-bridge/state/high_water_marks.json` with any new category bests. High-water marks never decay — scores must strictly exceed the current mark to update.

```
params: {"scores": {"reasoning": 0.74, ...}}
→ {"status": "ok", "updated_categories": {"reasoning": {"old": 0.71, "new": 0.74}}}
```

### eval_check_milestone()

Checks if any category has cleared its current milestone and should advance. Reads the last N score history entries per category, compares against the milestone's `unlock_score` and `unlock_consecutive` requirements, and if met, increments `current_milestone` in `world_model.json`. Logs every advancement to `memory/evolution_records/milestone-{cat}-L{n}.json`.

Called automatically by `loop_end_cycle` — you can also call it manually after reading scores.

```
→ {
    "status": "ok",
    "advanced": {"web_search": {"from": 0, "to": 1, "new_milestone_name": "Multi-Source Validation"}},
    "category_status": {"reasoning": {"milestone": 0, "consecutive": 1, "needed": 2, "unlock_score": 0.65}},
    "message": str
  }
```

---

## Correct EVAL Flow

```
1. eval_request(cycle=N, categories=["web_search"])   ← submit request, get request_id
2. eval_read_scores(eval_id=<request_id>)             ← wait for result, writes score_history
3. eval_check_regression(current_scores=<scores>)     ← auto-rollbacks if regression
4. eval_update_high_water(scores=<scores>)            ← update personal bests
   [loop_end_cycle calls eval_check_milestone]        ← auto-called at cycle end
5. loop_end_cycle()                                   ← archives hypothesis, clears session
```

---

## State Files

| File | Purpose |
|------|---------|
| `state/high_water_marks.json` | Best-ever score per category. Never decays. Synced from world_model.json at each cycle start. |
| `state/milestone_progress.json` | Consecutive clear counter per category for milestone advancement. |

---

## Rules

1. **Always call `eval_read_scores` with the `eval_id` from `eval_request`** — otherwise you may read a stale result from a previous cycle.
2. **eval_check_regression auto-rollbacks in code** — you do not need to call `evolve_rollback` manually after it. Check the `auto_rollback` field in the response to confirm.
3. **`snapshot_id` must exist in `session/evolution_target.json`** for auto-rollback to work. `forge_snapshot` writes it there — always call `forge_snapshot` before modifying any skill.
4. **High-water marks never decay.** They only go up.
5. **milestone advancement writes to world_model.json** — the next cycle will automatically use harder tasks for that category.

---
