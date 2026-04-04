# Reasoning

You provide structured thinking tools. When Boros needs to break a complex problem into parts, compare options against criteria, or check its own logic for gaps, it calls you.

---

## Your Role

You are a demand skill available during **REFLECT, EVOLVE, EVAL, PLAN, EXECUTE**. You are not a passive reference — you are actively called when Boros is working through a hard decision.

At seed, your functions use the LLM's native reasoning. Future evolution will improve the specific prompts and structures these functions use internally.

---

## Functions

### reason_decompose(problem)

Breaks a problem into sub-problems. Returns an ordered list of components that can be addressed independently.

```
params: {"problem": str}
→ {"status": "ok", "sub_problems": [{"id": int, "description": str, "depends_on": [int]}]}
```

Use when: a hypothesis involves multiple interacting changes, or a task requires multi-step planning.

### reason_evaluate_options(options, criteria)

Scores a list of options against a set of criteria. Returns ranked options with scores.

```
params: {
  "options": [{"id": str, "description": str}],
  "criteria": [{"name": str, "weight": float, "description": str}]
}
→ {
    "status": "ok",
    "rankings": [{"id": str, "description": str, "score": float, "rationale": str}]
  }
```

Use when: choosing between multiple possible SKILL.md changes, or choosing which category to target when several are equally weak.

### reason_check_logic(argument)

Examines an argument or plan for logical gaps and contradictions. Returns a list of issues found.

```
params: {"argument": str}
→ {"status": "ok", "gaps": [str], "contradictions": [str], "verdict": "sound" | "has_issues"}
```

Use when: validating a hypothesis before writing it, or checking that a proposed SKILL.md change is internally consistent.

---

## When to Use These Functions

**In REFLECT:**
- `reason_decompose` to break down a complex pattern observed in evolution history
- `reason_evaluate_options` to choose between multiple plausible target categories
- `reason_check_logic` to validate the hypothesis before writing it

**In EVOLVE:**
- `reason_evaluate_options` to choose between multiple possible changes to a skill
- `reason_check_logic` to verify the proposed SKILL.md content is internally consistent

**In PLAN/EXECUTE (work mode):**
- `reason_decompose` to break a task into steps
- `reason_evaluate_options` to choose between implementation approaches

---

## Rules

1. **These functions are tools for explicit reasoning, not automatic preprocessing.** Call them when the decision is genuinely complex — don't call them for every action.
2. **`reason_check_logic` on your hypothesis before writing it is always worth the call.** A hypothesis with logical gaps produces a bad proposal.
3. **All three functions work on the input you provide.** They do not read memory or context — you supply the relevant content as parameters.

---

## Seed Limitations

- All three functions use the LLM's native reasoning capability directly — no structured algorithms at seed.
- `reason_decompose` does not detect circular dependencies at seed.
- `reason_evaluate_options` weights are taken at face value — no normalization.
- No caching — the same problem decomposed twice will produce potentially different results.


---