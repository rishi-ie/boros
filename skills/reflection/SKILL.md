# Reflection

You provide the cognitive tools Boros needs to pause, synthesize historical failures, generate structured hypotheses for system edits, and reason deeply.

---

## Your Role

You act as a "Hybrid Universal Toolkit." You are no longer bound rigidly to the `REFLECT` stage of a cycle. Because Boros functions as an unconstrained agent navigating wild environments, you are treated as a dynamic analytical toolkit that the AI can explicitly invoke at will.

If Boros crashes a Python script during a `work` task, encounters a recursion error from a newly spawned daemon, or gets stuck parsing complex alien logic, Boros actively triggers your sophisticated toolings to step back, ingest heavy error traces, and generate analytical text directly into its logic stream.

---

## Functions

### reflection_analyze_trace(log_data)

A universal analytical scanner Boros calls explicitly to pass massive unstructured string chunks (like stderr/stdout from the `Skill Forge` environment) through a synthesized structural evaluation.

```
→ {"status": "ok", "synthesized_insight": str}
```

### reflection_write_hypothesis(rationale, expected_improvement, target_skill, trace_analysis)

A highly structured, data-backed formal thesis that Boros MUST formally write whenever it seeks to alter its own biological code or capabilities. This function now accepts `trace_analysis` which includes `weakest_category` and `recommendation` from the `reflection_analyze_trace` to ensure hypotheses are data-driven.

```
→ {"status": "ok", "hypothesis_id": str}
```

**CRITICAL HYBRID SAFETY CONSTRAINT:** 
Because Boros possesses ultimate software engineering power within `Meta-Evolution`, it cannot be allowed to impulsively rewrite its `SKILL.md` specs or `functions.py` scripts on an algorithmic whim. 

The underlying `Loop Orchestrator` strictly requires Boros to attach a valid, logged `hypothesis_id` matching an actively formulated `write_hypothesis()` execution event before it will ever execute a `Meta-Evolution` codebase mutation (`evolve_propose()`). You are the ultimate scientific safety gate enforcing rigorous analytical logging before brain surgery.

---

## Structural Requirements

- As Boros evolves to handle extreme contexts, Reflection MUST integrate transparently with the `SOTA Tiered Memory System`.
- `reflection_write_hypothesis` internally reads active instances of `Working Memory Core` Context and scores before writing the `hypothesis_id` into the system state for `EVOLVE` verification.


---