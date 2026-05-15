# META-LEARNING SYSTEM
## Change Type Success Tracking + RL Validation

---

## PURPOSE

Learn from past changes to optimize future ones.
Track what types of changes work for what capabilities.
Use RL validation to filter proposals before execution.

---

## CHANGE TYPES

| Type | Description | Best For |
|------|-------------|----------|
| `additive_code` | Add new functions | Low scores (<0.3) |
| `semantic_tune` | Edit SKILL.md / prompts | Medium scores (0.3-0.6) |
| `refactor_existing` | Rewrite existing code | Stalled improvement |
| `compositional` | Chain skills together | High scores (≥0.6) |

---

## SUCCESS RATES

Track success rate per change type using exponential moving average:

```
new_rate = 0.9 * old_rate + 0.1 * new_outcome
```

Where `new_outcome` = 1.0 for "improved", 0.0 for "regressed".

---

## ANTI-BRUTE-FORCE

If a file regressed 2+ times in a row, block further changes to it.
Must take a different approach before retrying.

```
file_history[target_file].consecutive_failures >= 2 → BLOCKED
```

---

## SUGGESTION LOGIC

1. If last change to this capability worked → try same type
2. If last change failed → try different type (best success rate)
3. Otherwise → pick highest success rate among non-blocked types

---

## RL VALIDATION

Use success rates as policy. Proposals evaluated as:

```
expected_reward = success_rate * confidence
risk = (1 - success_rate) * (1 - confidence)
```

| Action | Condition |
|--------|-----------|
| APPROVE | expected_reward > 0.2 |
| REVIEW | otherwise |
| BLOCK | file has consecutive failures |

---

## DATA PERSISTENCE

Stored in `session/meta_model.json`:

```json
{
  "version": "1.0",
  "change_type_success_rate": {
    "additive_code": 0.35,
    "semantic_tune": 0.20,
    "refactor_existing": 0.15,
    "compositional": 0.25
  },
  "capability_history": {
    "memory": {
      "last_change_type": "additive_code",
      "last_outcome": "improved",
      "total_improvements": 5,
      "total_regressions": 2
    }
  },
  "file_history": {
    "skills/memory/SKILL.md": {
      "consecutive_failures": 1,
      "last_change_type": "semantic_tune",
      "last_outcome": "no_change"
    }
  },
  "blocked_change_types": []
}
```

---

## IMPLEMENTATION

See: `meta_learning/meta_model.py`

Classes:
- `MetaLearningModel`: tracks success rates, suggests change types
- `RLValidation`: evaluates proposals, filters by risk/reward

---

## USAGE

```python
from meta_learning import MetaLearningModel, RLValidation

meta = MetaLearningModel(boros_root)
rl = RLValidation(meta)

# Get best change type
change_type = meta.suggest_change_type("memory")

# Evaluate proposal
evaluation = rl.evaluate_proposal({
    "change_type": "additive_code",
    "capability": "memory",
    "target_file": "skills/memory/SKILL.md"
})

# Record outcome
meta.record_outcome(
    change_type="additive_code",
    capability="memory",
    target_file="skills/memory/SKILL.md",
    outcome="improved",
    score_delta=0.05
)
```