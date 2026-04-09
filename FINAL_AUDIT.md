# BOROS FINAL AUDIT — 2026-04-10

All 20 infrastructure fixes from the previous audit are implemented. The system will no longer brick itself, crash without recovery, or ignore regressions. However, there are 4 remaining gaps that prevent Boros from being a truly complete self-evolving system.

---

## GAP 1 (CRITICAL): The LLM Cannot Query Its Own Learning History

**Problem:** The Evolution Ledger (`evolution_ledger.py`) is a powerful internal module — but it's `_internal`. The LLM has no tool to query it directly. The only exposure is passive injection into the system prompt (regression warnings). Boros can't ask:
- "What happened every time I touched `memory_commit_archival.py`?"
- "What's my success rate on the memory skill?"
- "What was the last approach that actually worked?"

The Knowledge Graph (`memory_kg_write`/`memory_kg_query`) IS in the manifest but the cycle prompt never instructs Boros to use it. It writes facts in, but reads nothing out.

**Fix:** Create `evolve_query_ledger` as a public LLM-callable tool. Update `cycle_prompt.md` to instruct querying both ledger and KG during REFLECT.

---

## GAP 2 (CRITICAL): World Model Has Only 1 Category

**Problem:** `world_model.json` has exactly one category: `memory`. Boros can only evolve toward memory mastery. The `reasoning`, `web-research`, `skill-forge`, and other skills are in the manifest and fully functional — but they have no evaluation path, no milestones, no scores. There is literally nowhere for Boros to go after memory is mastered.

**Fix:** Expand `world_model.json` to include `reasoning` and `web_search` categories with full milestones, anchors, rubrics, and related_skills.

---

## GAP 3 (CRITICAL): cycle_prompt.md Causes eval_id Hallucination

**Problem:** Step 22 of `cycle_prompt.md` says:
> `eval_read_scores` — pass the `eval_id` from step 21. This blocks until results arrive.

But `eval_request` returns a `request_id` (format: `req-XXXX`), not an `eval_id`. The instruction tells the LLM to "pass the eval_id" which doesn't exist yet — triggering the exact hallucination bug that has stalled cycles multiple times. The `pending_eval.json` fallback saves it, but the instruction itself is wrong.

**Fix:** Update the instruction to say "pass the `request_id` returned in step 21."

---

## GAP 4 (MEDIUM): BOROS.md and cycle_prompt.md Are Outdated

**Problem:** Both files were written before the 20 fixes. They don't mention:
- The evolution ledger (Boros doesn't know it exists)
- The KG tools `memory_kg_write`/`memory_kg_query` (not in cycle prompt)
- That anti-brute-force is now enforced programmatically (no need to self-police)
- That `eval_check_regression` auto-rollbacks (cycle prompt tells LLM to "roll back immediately" but it already happens automatically)
- The `memory_commit_archival` content requirements (Context:/Action:/Outcome: with 100-char min)
- Updated banned skills list (context-orchestration, skill-router are banned but not listed)
- The regression warnings injected into the system prompt (LLM should understand what they are)

**Fix:** Rewrite both files to reflect current system capabilities.

---

## Implementation

All 4 gaps are fixed in this session. See changes below.
