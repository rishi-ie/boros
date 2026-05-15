# MULTI-AGENT SYSTEM
## Reflector · Architect · Reviewer

---

## OVERVIEW

Boros uses a 3-agent architecture for self-evolution:

```
┌─────────────────────────────────────────────┐
│              ORCHESTRATOR                    │
│         (kernel.py — coordination)           │
└────────────────────┬────────────────────────┘
                     │
     ┌───────────────┼───────────────┐
     ▼               ▼               ▼
┌──────────┐   ┌──────────┐   ┌──────────┐
│ REFLECTOR│   │ ARCHITECT│   │ REVIEWER │
│          │   │          │   │          │
│ Analyze  │→  │ Design   │→  │ Evaluate │
│ Scores   │   │ Changes  │   │ Proposals│
└──────────┘   └──────────┘   └──────────┘
```

---

## AGENTS

### Reflector
**Role**: Analyze current performance, identify capability gaps, form hypotheses.

**Inputs**:
- Eval scores (high_water_marks.json)
- Cycle history
- Meta-learning model

**Outputs**:
- HYPOTHESIS messages (capability_gap, evidence, suggested_change_type, confidence)

**Behavior**:
- Reads lowest-scoring capabilities
- Suggests change type based on history
- Updates confidence based on outcomes
- Ignores capabilities that regressed 2x

### Architect
**Role**: Design concrete changes based on hypotheses.

**Inputs**:
- HYPOTHESIS messages from Reflector

**Outputs**:
- PROPOSAL messages (change_type, target_file, code_change, rationale, expected_impact, rollback_plan)

**Behavior**:
- Maps capability to target file
- Designs code change (additive / semantic / refactor / composition)
- Estimates expected score impact
- Revises proposals based on Reviewer feedback

### Reviewer
**Role**: Safety gate and quality check. All proposals must pass.

**Inputs**:
- PROPOSAL messages from Architect

**Outputs**:
- APPROVAL (proceed to execution)
- REJECTION (blocked — safety/regression)
- REVISION_REQUEST (quality issues to fix)

**Safety Checks**:
- Cannot modify: world_model.json, kernel.py, safety, self_modification_bounds
- Anti-brute-force: block file if regressed 2x in a row

**Quality Checks**:
- Not cosmetic-only (must have real logic changes)
- Not too small (< 50 chars unless semantic_tune)
- Has rationale
- Has rollback plan
- Expected impact ≥ 0.01

---

## MESSAGES

All agents communicate via typed messages through the AgentBus.

| Type | From | To | Purpose |
|------|------|-----|---------|
| HYPOTHESIS | Reflector | Orchestrator | "Improve this capability" |
| PROPOSAL | Architect | Reviewer | "Here's the change" |
| REVISION_REQUEST | Reviewer | Architect | "Fix these issues" |
| APPROVAL | Reviewer | Orchestrator | "Change approved" |
| REJECTION | Reviewer | Orchestrator | "Change blocked" |
| STATUS_REPORT | Any | Any | "Current state" |
| ESCALATION | Any | Orchestrator | "Needs attention" |

---

## AGENTBUS

In-memory pub/sub message bus.

```python
from agents.bus import get_bus

bus = get_bus()
bus.subscribe(MessageType.PROPOSAL, my_handler)
bus.publish(message)
```

---

## INTEGRATION

Agents are integrated into `agent_loop.py`:

```python
from agents import ReflectorAgent, ArchitectAgent, ReviewerAgent

reflector = ReflectorAgent(kernel)
architect = ArchitectAgent(kernel)
reviewer = ReviewerAgent(kernel)

# Start the bus
bus = get_bus()
bus.start()

# Run reflection phase
hypotheses = reflector.analyze()
for h in hypotheses:
    bus.publish(h)

# Architect responds to hypotheses with proposals
# Reviewer evaluates proposals
# Orchestrator acts on approvals
```

---

## CHANGE TYPES

| Type | Description | Best For |
|------|-------------|----------|
| additive_code | Add new functions | Low scores (<0.3) |
| semantic_tune | Edit SKILL.md / prompts | Medium scores (0.3-0.6) |
| refactor_existing | Rewrite code | Stalled improvement |
| compositional | Chain skills | High scores (≥0.6) |