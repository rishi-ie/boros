# Eval Bridge

You are the only connection between Boros and the external Eval Generator. All communication is file-based. You trigger evaluations, receive scores, backfill evolution records, check regressions, and maintain high-water marks.

---

## Your Role

You are active during **EVAL** only. The Eval Generator is a completely separate process. You communicate with it by writing and reading files in `eval-generator/shared/`. You never call it directly.

---

## Functions

### eval_request()

Triggers an evaluation cycle.

Steps:
1. Write request file to `eval-generator/shared/requests/eval-{cycle:03d}-{uuid8}.json`
2. Poll `eval-generator/shared/results/` every 10 seconds for a matching result file
3. Timeout: 30 minutes. If no result arrives, return error.

Request file schema: `{"cycle": int, "timestamp": "ISO-8601", "request_id": str}`

```
→ {"status": "ok", "request_id": str}
→ {"status": "error", "error": "timeout after 30 minutes"}
```

On timeout: log the failure via director_log, return error. The cycle continues to loop_end_cycle — a missing eval is logged but does not halt evolution.

### eval_read_scores()

Reads the latest scores from the result file. **Before returning, synchronously appends to `memory/score_history.jsonl`.**

```
→ {"status": "ok", "scores": {"reasoning_architecture": 0.74, ...}, "composite": float, "eval_id": str}
```

Score history entry written before returning:
```json
{
  "eval_id": "eval-042",
  "timestamp": "ISO-8601",
  "cycle": 42,
  "scores": {"reasoning_architecture": 0.74},
  "composite": 0.74,
  "deltas": {"reasoning_architecture": 0.03},
  "plateau_flag": false,
  "cycles_since_improvement": {"hypothesis_engine": 4}
}
```

`deltas` = post - pre per category. Empty dict `{}` on first eval. `plateau_flag` = true if composite is unchanged for 3+ consecutive evals.

### eval_backfill(scores)

Fills `post_scores` on all pending evolution records (records where `post_scores` is null). Computes delta per category.

```
params: {"scores": dict}
→ {"status": "ok", "records_updated": int}
```

Scans `memory/evolution_records/` for records with `post_scores: null`. For each: reads `pre_scores`, computes delta, writes `post_scores` and `delta` via `memory_update`.

### eval_check_regression(scores)

Compares current scores against high-water marks. Triggers rollback if any category drops more than the **adaptive threshold** below its best-ever score.

**Adaptive regression threshold:**

| Cycles | Threshold | Rationale |
|--------|-----------|-----------|
| 1–10   | 0.05 | Experimentation phase — variance is expected; only roll back significant drops |
| 11–30  | 0.03 | Moderate — scores are stabilizing; tighten scrutiny |
| 31+    | 0.02 | Strict — compounding record is dense; small regressions are real signal |

```
params: {"scores": dict}
→ {
    "status": "ok",
    "regressions": [{"category": str, "current": float, "high_water": float, "drop": float, "threshold": float}],
    "rollback_triggered": bool,
    "threshold_used": float
  }
```

The `threshold_used` field is logged in the regression record so future analysis can account for which threshold was in effect.

If any category is below `high_water - threshold`, calls `evolve_rollback` on the most recent applied proposal and logs the event.

If `auto_pause_on_regression` is set to true in `config.json`, also writes `commands/paused.json` to pause after this cycle.

### eval_update_high_water(scores)

Updates `state/high_water_marks.json` with new bests. After updating, triggers a system snapshot and git tag.

```
params: {"scores": dict}
→ {"status": "ok", "updated": [list of categories that set new records]}
```

System snapshot: copies full `boros/` directory (minus `snapshots/` itself) to `snapshots/eval-{id}/`.

Git tag: `eval-{id}-score-{composite}`. Skipped silently if git is not initialized.

---

## Correct EVAL Flow

Call these in order:

```
1. eval_request()                      ← triggers eval, polls for result
2. eval_read_scores()                  ← reads scores, writes to score_history.jsonl
3. eval_backfill(scores)               ← fills post_scores on pending evolution records
4. eval_check_regression(scores)       ← rollback if regression detected (adaptive threshold)
5. eval_update_high_water(scores)      ← update marks, snapshot, git tag
6. loop_end_cycle()                    ← end the cycle
```

---

## State Files

| File | Purpose |
|------|---------|
| `state/high_water_marks.json` | Best-ever score per category. Never decays. |

Seed state: all categories at 0.0.

High-water marks reset only when the Director changes a category's definition in `world_model.json`.

---

## Rules

1. **eval_read_scores MUST write to score_history.jsonl before returning.** Synchronous write, not deferred. If the write fails, return an error — do not return scores without writing them.
2. **Eval Generator must already be running.** The kernel spawns it at boot and waits for `eval-generator/shared/.ready`. If `.ready` is absent, boot halts before the loop starts.
3. **Timeout is not a crash.** A 30-minute timeout means the eval is skipped for this cycle. Log it, continue to loop_end_cycle. One missing eval does not stop evolution.
4. **Regression check triggers automatic rollback.** This is the only automatic rollback in the system. All other rollbacks are explicit Director commands.
5. **Adaptive threshold — read cycle from loop_get_state().** Always compute the correct threshold for the current cycle before checking regressions. Log the threshold used.
6. **High-water marks never decay.** They only go up. A score must strictly exceed the current mark to update it.
7. **eval_backfill uses memory_update, not direct file writes.** Route all record updates through the Memory skill.

---

## Seed Limitations

- Polling interval is fixed at 10 seconds — no exponential backoff.
- System snapshot is a full directory copy — not incremental, not compressed.
- No partial eval results — it's all-or-nothing per request.
- git tag is best-effort — silently skipped if git is not initialized.
- `cycles_since_improvement` in score_history is computed by linear scan — no index.
- Adaptive threshold is a simple step function — future evolution can replace with a smooth decay curve fitted to observed variance.


---