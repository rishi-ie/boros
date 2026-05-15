# SKILL FORGE
## Skill Composition Engine

---

## PURPOSE

Compose multiple skills into workflows using operators.
Enables emergent capabilities through skill chaining.

---

## OPERATORS

### SEQUENCE
Run steps one after another, passing result to next.

```
workflow:
  name: "analyze_and_store"
  type: "sequence"
  steps:
    - skill: memory_retrieve
      params: {query: "recent work"}
    - skill: reasoning_decompose
      params: {problem: "from_retrieve"}
    - skill: skill_execute
      params: {action: "apply"}
    - skill: memory_store
      params: {insights: "results"}
```

### PARALLEL
Run steps concurrently, collect all results.

```
workflow:
  name: "web_research"
  type: "parallel"
  steps:
    - skill: web_search
      params: {query: "topic + latest news"}
    - skill: web_search
      params: {query: "topic + technical docs"}
    - skill: web_search
      params: {query: "topic + github"}
```

### BRANCH
Run one of N branches based on condition.

```
workflow:
  name: "quality_gate"
  type: "branch"
  branches:
    - condition: tests_passed
      skill: publish
    - condition: tests_failed
      skill: fix_and_retry
  default: log_warning
```

### LOOP
Repeat until condition met or max iterations.

```
workflow:
  name: "api_retry"
  type: "loop"
  steps:
    - skill: api_call
      params: {endpoint: "target"}
    - skill: validate_result
      params: {}
  until: result.success
  max_iterations: 5
```

---

## EXAMPLE WORKFLOWS

### Evolution Cycle
```python
sequence_workflow("evolution_cycle", [
    ("memory_retrieve",      {"query": "capability_gaps"}),
    ("reflector_analyze",    {"focus": "lowest_score"}),
    ("architect_design",     {"hypothesis": "from_reflector"}),
    ("reviewer_evaluate",    {"proposal": "from_architect"}),
    ("executor_apply",       {"approved": "from_reviewer"}),
    ("eval_run",             {"change_id": "from_executor"}),
    ("meta_learn_record",    {"outcome": "from_eval"}),
    ("memory_store",         {"insights": "all_above"}),
])
```

### Research Pipeline
```python
parallel_workflow("web_research", [
    ("web_search", {"query": "topic + news"}),
    ("web_search", {"query": "topic + docs"}),
    ("web_search", {"query": "topic + github"}),
])
```

### Robust API Call
```python
loop_workflow("api_retry", [
    ("api_call",    {"endpoint": "target"}),
    ("validate",    {}),
], until=lambda r: r and r.get("success"), max_iter=5)
```

---

## IMPLEMENTATION

See: `skills/skill-forge/composer.py`

Classes:
- `OperatorType`: SEQUENCE, PARALLEL, BRANCH, LOOP
- `SkillStep`: skill_name, params, input_from
- `Workflow`: name, operator, steps, condition, max_iterations, on_error
- `SkillComposer`: execute workflows, register skills, cache results

---

## CAPABILITY BUILDING

Skill Forge enables emergent capabilities by combining existing skills.
When a new combination produces strong results, it can be:
1. Saved as a new skill
2. Proposed for world model integration
3. Used as a template for future work