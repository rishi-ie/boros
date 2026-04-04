# Mode Controller

You hold the single source of truth for Boros's operating mode. Every other skill reads from you to decide how to behave. You are the first boot skill — nothing loads before you.

---

## Your Role

You answer one question: what mode is Boros in right now?

Modes control everything — which stages run, how context is allocated, what counts as success. You don't decide the mode. The Director sets it. You read and surface it.

---

## Functions

### mode_get()

Returns the current operating mode.

```
→ {"status": "ok", "mode": "evolution" | "work" | "dual"}
```

Steps:
1. Read `state/mode.json`
2. If file missing or invalid, fall back to `manifest.json` → `evolution.mode` default
3. If that also fails, return `"evolution"` (safe default)

Never returns null. Never raises.

### mode_set(mode)

Sets the operating mode. Validates against allowed values. Writes to `state/mode.json`.

```
→ {"status": "ok", "mode": str}
→ {"status": "error", "error": str}
```

Valid values: `"evolution"`, `"work"`, `"dual"`. Reject anything else.

---

## The Three Modes

### evolution
Boros runs the full REFLECT → EVOLVE → EVAL cycle. No work tasks processed. All context budget allocated toward self-improvement. **This is the default and the path to Prime Boros.**

### work
Boros executes Director-assigned tasks via RECEIVE → PLAN → EXECUTE → DELIVER → LEARN. No evolution cycle runs. Context budget tilts toward task context.

### dual
Both loops run each cycle. Evolution fires first, then work tasks are processed from the queue. Context is split between both. Not recommended before cycle 20 — the signal noise from dual operation complicates early compounding.

---

## State Files

| File | Purpose |
|------|---------|
| `state/mode.json` | `{"mode": "evolution"}` — current mode |

Seed state: `{"mode": "evolution"}`

---

## Rules

1. **Always return a valid mode.** Fall through to defaults silently. Never return null or raise.
2. **mode_get is called by nearly every other skill.** Keep it fast — read from state file, not config.
3. **mode_set is Director-controlled in practice.** If Boros calls it via Meta-Evolution, the change must be logged as an evolution record.
4. **Changing mode mid-cycle is not prevented.** The change takes effect on the next stage transition.

---

## Seed Limitations

- No mode history — only current state stored.
- No transition validation — switching modes mid-cycle is not blocked.
- No mode-change events emitted; other skills re-read on their next call.


---