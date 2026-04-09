# Context Orchestration

You load and assemble the working context that gets injected into the system prompt at cycle start. You write a context manifest to `session/context_manifest.json` and return its contents.

---

## Your Role

You consolidate the memory sources Boros needs for the current cycle into one place. The system prompt in `agent_loop.py` builds its blocks from multiple sources — you are responsible for the memory-specific portion: recent evolution records, recent experiences, recent scores, the active hypothesis, and high-water marks.

---

## What You Actually Load

When `context_load` is called:

1. **Recent evolution records** — last 5 files from `memory/evolution_records/*.json`, sorted by mtime. Includes applied proposals, rejected proposals, and hypothesis outcome archives.
2. **Recent experiences** — last 5 files from `memory/experiences/exp-*.json`, sorted by mtime. Written by `memory_commit_archival`.
3. **Recent scores** — last 5 lines from `memory/score_history.jsonl`.
4. **Active hypothesis** — `session/hypothesis.json` if it exists (cleared at cycle end after archival).
5. **High-water marks** — `skills/eval-bridge/state/high_water_marks.json`.

The assembled manifest is saved to `session/context_manifest.json` and returned.

---

## Functions

### context_load()

Loads all context sources listed above. Returns the manifest as a dict.

```
params: {}   ← no parameters
→ {
    "status": "ok",
    "loaded": true,
    "manifest_keys": ["evolution_records", "recent_experiences", "recent_scores", "hypothesis", "high_water_marks"],
    "content": {
        "evolution_records": [...],
        "recent_experiences": [...],
        "recent_scores": [...],
        "hypothesis": {...} | null,
        "high_water_marks": {...}
    }
  }
```

Note: `content` is a dict, not a formatted string. The system prompt in `agent_loop.py` handles formatting.

### context_get_manifest()

Returns the saved manifest from `session/context_manifest.json` without re-loading from disk.

```
→ {"status": "ok", ...manifest dict...}
```

---

## What Is NOT Implemented

- **Associative Whisper / semantic search** — not implemented. Use `memory_search_sql` manually if you need semantic retrieval.
- **Identity block, mode/task summary injection** — handled by `agent_loop.py`'s `build_system_prompt()`, not by this skill.
- **Formatted `=== SECTION ===` string output** — content is returned as a raw dict, not a formatted string.

---

## Rules

1. **Call `context_load` at the start of REFLECT** — before analyzing scores or writing a hypothesis. This ensures `session/context_manifest.json` is current.
2. **Experiences are read from `memory/experiences/exp-*.json`** — individual files written by `memory_commit_archival`. Not from `experiences.jsonl` (that file does not exist).
3. **Evolution records include hypothesis outcomes** — after Day 1 fixes, `loop_end_cycle` archives each hypothesis to `memory/evolution_records/hyp-cycle{N}.json`. These appear in context so you can see what was tried and what the outcome was.

---
