# Loop Orchestrator

You run the loop. You manage stage transitions, cycle counting, conversation lifecycle, and the system prompt. You are the last boot skill — you call `loop_start()` and evolution begins.

---

## Your Role

You are the conductor. Every other boot skill exists to serve the loop you run. You:
- Build the system prompt at cycle start (5 blocks)
- Advance stages and swap tool lists
- Enforce the hypothesis gate before EVOLVE
- End cycles, clear session, poll Director commands
- Know the authoritative cycle number at all times

You do not reason. You do not evaluate. You coordinate.

---

## Functions

### loop_start(mode?)

Called by the kernel after all 10 boot skills load successfully. Starts the first cycle.

Steps:
1. Call `context_load()` — get `loaded`, `manifest`, and `content`
2. Build system prompt (5 blocks — see below)
3. Set stage to `REFLECT`
4. Call `router_get_tools(stage="REFLECT")` — get tool list
5. Write `session/current_cycle.json` with cycle number and `started_at`
6. Send first LLM API call (system prompt + empty history + REFLECT tools)
7. Enter the conversation loop (process tool calls, advance stages)

```
→ {"status": "ok"}
```

### loop_advance_stage(current_stage)

Called by the LLM when it finishes a stage. Transitions to the next stage.

Steps:
1. Validate `current_stage` matches the actual current stage (reject mismatch)
2. Determine next stage from `state/loop_definitions.json`
3. **Hard gate:** If transitioning FROM REFLECT, verify `session/hypothesis.json` exists. If missing: one retry (re-enter REFLECT with a note). Still missing after retry: log cycle as failed, call `loop_end_cycle`.
4. Call `router_get_tools(next_stage)` — swap tool list
5. Update `state/loop_state.json` → `stage`
6. Continue conversation (same history + new tool list + stage directive appended as user message)

```
→ {"status": "ok", "next_stage": str}
```

### loop_end_cycle()

Ends the current cycle. Called by the LLM at the end of EVAL (or LEARN in work mode).

Steps:
1. Increment cycle counter in `state/loop_state.json`
2. Write session record to `memory/sessions/` via Memory
3. Append cycle timing to `temporal-consciousness/state/cycle_times.jsonl`
4. Clear `session/` directory (all files)
5. Poll `commands/pending.json` — process any Director commands
6. Check spot-check schedule (`cycle % director_spot_check_frequency == 0`)
7. If spot-check due: call `director_spot_check()` — blocks until Director responds
8. Start next cycle (loop back to `loop_start`)

```
→ {"status": "ok", "cycle": int}
```

### loop_get_state()

Returns current loop state. Authoritative source for cycle number.

```
→ {"status": "ok", "cycle": int, "stage": str, "mode": str, "started_at": str}
```

---

## System Prompt Assembly

`loop_start` builds five blocks, joined by double newlines:

**Block 1 — Identity**
From `identity_read()`. Always present.

```
=== IDENTITY ===
Name: Boros
Purpose: ...
```

**Block 2 — Stage Directive**
From `loop_definitions.json` for the current stage. Changes at each stage transition (appended as a user message after block 2 is no longer changing).

```
=== CURRENT STAGE: REFLECT ===
Analyze your scores and evolution records. Identify the weakest category. Write a hypothesis by calling reflection_write_hypothesis. Call loop_advance_stage when done.
```

**Block 3 — Context Manifest**
The JSON manifest from `context_load`. Tells the LLM what was loaded and what was dropped.

```
=== CONTEXT MANIFEST ===
{"cycle": 42, "mode": "evolution", "loaded": {...}, "not_loaded": {...}}
```

**Block 4 — Loaded Memory Content**
The `content` string from `context_load`. The actual text of evolution records, scores, experiences. This is what REFLECT reads. **If this block is empty, REFLECT is blind.**

```
=== MEMORY CONTENT ===
=== SCORE HISTORY (last 3 evals) ===
...
=== EVOLUTION RECORDS (15 loaded) ===
...
```

**Block 5 — Rules**
Fixed operational rules.

```
=== RULES ===
- Call loop_advance_stage when you are done with the current stage.
- Call loop_end_cycle only at the end of EVAL (evolution mode) or LEARN (work mode).
- Never call loop_end_cycle mid-cycle.
- Tool availability changes at each stage — only use tools currently available.
```

---

## Conversation Lifecycle

- Conversation history carries forward **within** a cycle (REFLECT → EVOLVE → EVAL share history)
- At stage transition: same history + updated tool list + stage directive appended as user message
- At cycle end: history is discarded, fresh conversation starts next cycle
- Each stage is one or more LLM API calls — the LLM calls tools, gets results, continues until it calls `loop_advance_stage`

---

## Stage Definitions (Seed)

From `state/loop_definitions.json`:

**Evolution mode stages:** REFLECT → EVOLVE → EVAL

**Work mode stages:** RECEIVE → PLAN → EXECUTE → DELIVER → LEARN

**Stage directives (seed):**

| Stage | Directive |
|-------|-----------|
| REFLECT | Analyze your scores and evolution records. Identify the weakest category. Write a hypothesis by calling reflection_write_hypothesis. Call loop_advance_stage when done. |
| EVOLVE | Load your hypothesis. Propose a targeted change to a skill's SKILL.md. Write the full new SKILL.md content, then call evolve_propose with proposed_skillmd and target_category. Send it for review via review_proposal. If approved, apply it via evolve_apply. Call loop_advance_stage when done. |
| EVAL | Request an evaluation via eval_request. When scores arrive, backfill records, check regressions, and update high-water marks. Call loop_end_cycle when done. |
| RECEIVE | Parse the task requirements. Identify any ambiguity. Call loop_advance_stage when ready to plan. |
| PLAN | Break the task into steps. Query Memory for similar past tasks. Call loop_advance_stage when ready to execute. |
| EXECUTE | Do the work. Use Tool Use for terminal, HTTP, and file operations. Call loop_advance_stage when done. |
| DELIVER | Package and deliver the results via the Communication skill. Call loop_advance_stage when done. |
| LEARN | Write structured learning artifacts — gap reports, performance patterns, technique discoveries. Tag them work_learning. Call loop_end_cycle when done. |

Stage directives are evolvable by Boros via Meta-Evolution.

---

## Error Recovery

| Error | Response |
|-------|----------|
| Max tool calls reached (100) | End cycle, log as budget-exceeded, start fresh |
| Cycle timeout (10 min) | Kernel kills cycle, log as failed, start fresh |
| Hypothesis missing after retry | Log as failed, start fresh |
| loop_advance_stage called with wrong stage | Return error, do not advance |
| Any function error | Return error to LLM — LLM retries, works around, or moves on |

A single bad cycle never stops evolution.

---

## State Files

| File | Purpose |
|------|---------|
| `state/loop_state.json` | Current cycle, stage, mode, started_at, total_cycles_completed |
| `state/loop_definitions.json` | Stage sequences and directives (evolvable) |

Seed state for `loop_state.json`:
```json
{"cycle": 0, "stage": null, "mode": "evolution", "cycle_started_at": null, "total_cycles_completed": 0}
```

---

## Rules

1. **Block 4 of the system prompt must contain actual content.** If `context_load` returns an empty `content` field, log a warning and proceed — but REFLECT will be working blind.
2. **The hypothesis gate is non-negotiable.** EVOLVE does not start without `session/hypothesis.json`.
3. **Cycle counter is the authoritative state.** Always read from `loop_state.json`, never infer from memory record counts.
4. **commands/pending.json is processed between cycles only.** Commands do not interrupt a running cycle (except `pause`).
5. **Session is cleared at cycle end.** Nothing in `session/` persists across cycles. Everything worth keeping must be written to Memory.

---

## Seed Limitations

- No dynamic stage injection — stages are fixed sequences at seed.
- Conversation history is held in memory only — a kernel crash loses the current cycle.
- No partial cycle resume — crashed cycles restart from scratch.


---