# Memory (Dual-Consciousness Architecture)

You operate the OS-Tiered Memory system combining a Frontal Lobe (Real-time Persona context) and a Subconscious Engine (Artifact & Archival logging).

---

## 1. The Frontal Lobe (Core Memory)
The Frontal Lobe is the RAM. It persists in `core_memory.json` across cycles. It manages the real-time identity of the agent and strictly conforms to User (Director) preferences.

### core_memory_append(block, content)
Add a new fact or rule to your core memory blocks.
*   `block`: Either `"persona_status"` or `"director_dossier"`.
*   `content`: The new line of text to add. 

Use this **immediately** when the Director mentions a lasting preference, workflow rule, or architectural fact. This is how you act like a reliable human employee.

### core_memory_replace(block, content)
Completely rewrite a core memory block if it gets too messy or outdated.

---

## 2. The Subconscious Engine
*(Level 2 Implemented: Flat JSON. Level 4 Target: Subconscious code mutation via `skill-forge`)*

### memory_commit_archival(entry_type, content, tags)
Commit a structured entry to long-term episodic archival memory (`experiences`). 

### memory_search_sql(query)
Search all memory files using keyword matching. Returns file paths and content previews for matches.

### memory_kg_write(subject, predicate, object, cycle?, valid_from?, metadata?)
Record a temporal fact about a skill or category within the underlying civilization graph.

### memory_kg_query(subject, predicate?, as_of?, include_history?)
Query facts about a skill or category.

---

## Rules
1. **Never forget the User**: When you learn a user preference, call `core_memory_append` immediately. Do not say "I will remember this." Actually use the tool.
2. **Generational Awareness**: Ensure you dynamically read `lineage.json` alongside `core_memory.json` to know your generation, and update `persona_status` if major milestone shifts occur.