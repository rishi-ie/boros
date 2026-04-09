# Memory

You are the central data storage layer for Boros's persistent state across evolution cycles.

---

## Current Implementation (Level 2)

The memory system currently uses flat JSON/JSONL file storage:
- **Episodic**: `memory/experiences/*.json` — individual observation/lesson files
- **Score History**: `memory/score_history.jsonl` — chronological evaluation scores
- **Evolution Records**: `memory/evolution_records/*.json` — past proposals and diffs
- **Session Buffer**: `memory/sessions/current_buffer.json` — key-value working memory
- **Search**: Keyword-based grep through all memory files

---

## Functions

### memory_page_in(source, limit, skill?, outcome?, tags?)

Load entries from a specific memory source into the current context.

Sources: `scores`, `experiences`, `evolution_records`, `sessions`, `session_buffer`

**Filtering (evolution_records source):**
- `skill` — partial match against `target_skill` field (e.g. `"reasoning"` finds all cycles targeting reasoning)
- `outcome` — exact match: `improved`, `regressed`, `neutral`, `baseline`

**Filtering (experiences source):**
- `tags` — array of strings; returns entries matching any tag

Use this in REFLECT to load targeted history:
```
memory_page_in({"source": "evolution_records", "skill": "reasoning", "limit": 8})
→ last 8 evolution cycles that targeted reasoning, newest first

memory_page_in({"source": "evolution_records", "skill": "reasoning", "outcome": "regressed"})
→ only the cycles that made reasoning worse — avoid repeating these
```

Each evolution_record entry contains: `target_skill`, `rationale`, `actual_outcome`, `score_delta`, `score_before`, `score_after`, `cycle`, `timestamp`.

```
→ {"status": "ok", "source": str, "entries": list, "count": int}
```

### memory_page_out(key, value)

Write a key-value pair to the current session buffer. Used for short-term working memory that persists within a session.

```
→ {"status": "ok", "key": str}
```

### memory_search_sql(query)

Search all memory files using keyword matching. Returns file paths and content previews for matches.

```
→ {"status": "ok", "query": str, "matches": list, "total": int}
```

### memory_commit_archival(entry_type, content, tags)

Commit a structured entry to long-term archival memory (experiences). Entry types: `lesson`, `observation`, `fact`.

```
→ {"status": "ok", "entry_id": str}
```

### memory_kg_write(subject, predicate, object, cycle?, valid_from?, metadata?)

Record a temporal fact about a skill or category. Facts have validity windows — you can query what was true at a specific cycle, not just right now.

**Common predicates:**
- `has_score` — `("reasoning", "has_score", "0.72", cycle=5)`
- `was_modified` — `("reasoning", "was_modified", "reflection.py", cycle=5)`
- `achieved_milestone` — `("reasoning", "achieved_milestone", "L1", cycle=12)`
- `caused_delta_in` — `("reasoning", "caused_delta_in", "web_search:+0.01", cycle=5)` — cross-category link
- `target_of` — `("reflection", "target_of", "hyp-abc123", cycle=5)`

Call after every successful evolution (record `was_modified`) and after every eval (record `has_score`).

```
→ {"status": "ok", "triple_id": int}
```

### memory_kg_query(subject, predicate?, as_of?, include_history?)

Query facts about a skill or category.

```
memory_kg_query({"subject": "reasoning"})
→ all currently valid facts about reasoning

memory_kg_query({"subject": "reasoning", "predicate": "has_score", "include_history": true})
→ full score history for reasoning across all cycles

memory_kg_query({"subject": "reflection", "as_of": "2026-04-01T00:00:00Z"})
→ what was true about reflection on April 1st
```

```
→ {"status": "ok", "subject": str, "facts": list[{predicate, object, valid_from, cycle}], "count": int}
```

---

## Evolution Target (Level 4)

To reach Level 4 on the Memory & Continuity world model category, this skill needs:

1. **Structured Retrieval**: Replace keyword grep with SQLite for structured queries over experiences, scores, and evolution records. Enable queries like "find all failed mutations targeting memory" or "get score trend for last 10 cycles".

2. **Semantic Search**: Add vector similarity search (using sentence embeddings) for archival memory. Enable queries like "find past approaches similar to improving memory persistence".

3. **Automatic Pattern Extraction**: After each cycle, automatically extract patterns from episodic memory into semantic memory (e.g., "mutations to X skill tend to improve scores by Y%").

4. **Memory-Conditioned Decisions**: Before each evolution decision, automatically retrieve and surface relevant past experiences. The agent should never repeat a known-failed approach.

5. **Consistency Checks**: Detect when the agent is about to repeat a previously failed strategy, or when new evidence contradicts stored conclusions.

---

## Rules

1. **Active Usage**: Boros MUST use `memory_page_in` when facing tasks that benefit from historical context. Without it, Boros has amnesia.
2. **Persistence**: All memory operations write to disk. Nothing is lost between cycles.
3. **No External Dependencies**: All storage is local filesystem. No cloud databases, no API calls.
4. **Evolution Path**: The functions in this skill are the PRIMARY evolution targets for the `memory_continuity` world model category. Improving these functions directly improves Boros's score.

---