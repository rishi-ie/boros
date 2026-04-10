# Boros

Boros is an autonomous, self-evolving AI system that rewrites its own Python capabilities, tests those changes in an isolated sandbox, and automatically rolls back any modifications that decrease its performance scores.

Boros operates without fixed prompts or logic trees. It uses a "world model" to understand its objectives, modifies its own base code to achieve them, and leverages independent evaluators to verify success.

---

## The 4-Stage Evolution Loop

Boros operates continuously through an `agent_loop.py` engine, executing a core 4-stage process:

### 1. REFLECT
Boros reads its `logs/execution_cycles.log` and past evaluation scores. It queries the `eval-bridge` for its highest achieved scores and analyzes `task_log.jsonl` to find specific points of failure. By comparing its past errors with the goals in the `world_model.json`, it generates a hypothesis for a codebase fix or improvement.

### 2. EVOLVE
With a hypothesis established, the `meta-evolution` module alters the codebase. Boros can:
- Modify `SKILL.md` instruction files to change its behavioral logic.
- Edit existing Python scripts inside the `functions/` repository.
- Use `skill-forge` to synthesize entirely new skill directories and Python tools.

### 3. VALIDATE
Once the changes are made, the `meta-evaluation` module takes over. An independent review LLM—which has no context regarding the prior edits—generates adversarial test scenarios through the `eval-generator` sandbox. Boros is tested against these generated scenarios and scored on a strict 0.0 to 1.0 composite metric.

### 4. COMMIT / ROLLBACK
Boros relies on a strict snapshot rollback mechanism. If the validation score equals or exceeds the High-Water Mark stored in `state/high_water_marks.json`, the new code is committed and hot-reloaded into the running kernel. If the score drops, the snapshot daemon restores the `skills/` directory from the `snapshots/` folder, erasing the failed mutation.

---

## Generational Forking & Adaptation

Boros allows operators to freeze the self-evolution process and transition the agent into a "deployment" state via Generational Forking.

- **Forking (`fork`)**: When the `fork` command is issued, Boros pauses evolution and increments its generation epoch in `lineage.json`. It assumes the `boros-fork` state, operating as an employee agent that answers user tasks without structurally modifying itself.
- **Asynchronous Adaptation (`adapt`)**: While in a `boros-fork` state, Boros can run background reflection tasks (scheduled via `adapt-config`). It will process field operations and identify latent edge cases without aggressively mutating the core structure.
- **Re-Evolving (`re-evolve`)**: When the deployment concludes, the operator types `re-evolve`. Boros compiles the deployment logs into an `adapt_seed.json` matrix. It resumes full evolution mode, specifically targeting the gaps it discovered during real-world task execution.

---

## The World Model

Boros does not rely on hardcoded directives. It is governed by `world_model.json`, a configuration file containing multi-tiered rubrics, milestones, and unlock scores.

When Boros clears a scoring milestone during validation, `eval_check_milestone` reads the `world_model.json` to advance the system to more difficult trials. To change Boros's strategic trajectory, you edit the world model directly.

```json
{
  "categories": {
    "cognitive_memory": {
      "name": "Episodic Persistence Mastery",
      "weight": 5.0,
      "related_skills": ["memory", "reasoning"],
      "rubric": {
        "level_1": "Fails to create database records",
        "level_2": "Can log data, fails to retrieve contextually",
        "level_3": "Perfect recall, fails associative linking",
        "level_4": "Achieves multi-hop temporal semantic memory"
      }
    }
  }
}
```

---

## System Architecture

The codebase relies on modular skill directories rather than monolithic handlers:
- `kernel.py`: Manages registry loading, snapshots, and API routing.
- `agent_loop.py`: Executes the Reflect -> Evolve -> Validate process.
- `skills/`: The live codebase modified by Boros. Contains modular sub-skills (`reflection`, `meta-evolution`, `eval-bridge`, `skill-forge`, `memory`, `director-interface`).
- `eval-generator/`: An isolated parallel scoring sandbox.

---

## Quick Start

### 1. Requirements

- Python 3.11+
- API Keys: `GEMINI_API_KEY` (Default), `ANTHROPIC_API_KEY`, or `OPENAI_API_KEY`.

### 2. Installation

```bash
git clone <repo-url>
cd boros
pip install -r requirements.txt
cp .env.template .env
```
Populate the `.env` file with your API keys. Provider priority is defined in `config.json`.

### 3. Startup

```bash
python start.py
```

Upon boot, the Director Interface provides two options:
1. `evolve`: Start the autonomous self-improvement loop.
2. `work`: Run Boros strictly for task execution.

### 4. Director Commands

Enter these commands at the `boros>` prompt during execution:
- `status`: Show the current cycle, generation epoch, and highest scores.
- `evolve` / `work`: Switch between continuous mutation and standard execution.
- `fork`: Freeze progress as a static deployment agent (`boros-fork`).
- `re-evolve`: Extract insights from the field memory and resume evolution.
- `adapt`: Run manual adaptation reflections during a fork.
- `adapt-config <time>`: Schedule background reflections (e.g., `2d`, `12h`).
- `pause` / `resume`: Halt and resume orchestration threads.
- `logs [n]`: Stream cycle diagnostics.

---

## Boros in Action — Real Evolution Logs

The following is a real run. No edits, no cherry-picking. This is what Boros actually does when you start it. 
just with gemini-2.5-flash, no other models were used, no human intervention

---

### The Starting State

Cycle 14. Boros boots and reads its current scores:

```
eval_read_scores → {"scores": {"web_search": 0.333}, "composite": 0.333}
```

Web search is failing 2 out of 3 eval tasks. Boros reads its evolution history, finds the pattern, and decides where to look.

---

### Cycle 14 — Diagnosing a Silent Failure

Boros opens `skills/web-research/functions/research_search_engine.py` and reads it. It finds this:

```python
except ImportError:
    pass
except Exception:
    pass
```

Silent failure. When the DuckDuckGo search library throws an error, nothing is logged — Boros falls back to a less reliable method and has no idea why. It proposes a fix: replace the `pass` statements with actual error logging.

The proposal goes to the **independent review board** (a separate LLM that has no knowledge of the evolution loop and evaluates the diff on its own):

```
verdict: "apply"
reason: "This adds meaningful programmatic execution logic by providing
         diagnostic output when exceptions occur..."
```

The change is applied **live without restarting**:

```
evolve_apply → {"status": "ok", "message": "Proposal applied and web-research LIVE reloaded."}
```

---

### Cycle 15 — First Improvement: Memory Score 0.0 → 0.709

Boros runs a full evaluation across all categories. The `memory` skill has never been scored before — it comes back at **0.625**. The evaluator's breakdown:

```
"It attempted to record an episodic memory using memory_commit_archival
 but initially failed because 'content required', indicating it tried
 to commit an empty or malformed memory entry."
```

Boros first tries the safest approach — editing the `SKILL.md` semantic rules to describe the expected format. The review board **rejects it**:

```
verdict: "reject"
reason: "This does not add any meaningful programmatic execution logic,
         alter control flow, modify algorithms, or change structural
         capabilities within the codebase."
```

Correct rejection. Boros rolls back and tries a real code change instead. It modifies `memory_commit_archival.py` to enforce that every `lesson` or `observation` entry must contain explicit `Context:`, `Action:`, and `Outcome:` phrases:

```python
# Before
if not content:
    return {"status": "error", "message": "content required"}

# After
if entry_type in ["lesson", "observation"]:
    required_phrases = ["Context:", "Action:", "Outcome:"]
    if not all(phrase in content for phrase in required_phrases):
        return {"status": "error", "message": f"content must include: {required_phrases}"}
```

Review board approves it. Evaluation runs. Score:

```
memory: 0.625 → 0.709   ✔ improvement
eval_check_regression → {"has_regression": false, "improvements": {"memory": {"delta": 0.709}}}
```

High-water mark set at **0.709**. Cycle committed.

---

### Cycle 17 — Pushing Further, Getting Pushed Back

Score is 0.709 but inconsistent — individual task scores are `[0.5, 1.0, 0.5]`. Boros reads the evaluator's feedback:

```
"initial tool-specific formatting error despite understanding what
 constitutes an episodic memory"
```

It tries a SKILL.md change again to add a worked example of correct content format. The review board rejects it again — cosmetic. Boros rolls back and instead rewrites the validation logic in Python to actively parse and reconstruct malformed content rather than just reject it:

```python
# Extract existing parts
idx_ctx = content.find("Context:")
idx_act = content.find("Action:")
idx_out = content.find("Outcome:")

# Reconstruct in correct order with placeholders for missing parts
content = f"Context: {ctx or '[unspecified]'}. Action: {act or '[unspecified]'}. Outcome: {out or '[unspecified]'}."
```

Review board approves:

```
verdict: "apply"
reason: "Transitions from a passive validator into a proactive formatter...
         ensuring a consistent and structured output regardless of minor
         input variation."
```

---

### Cycles 18–22 — Regression, Recovery, Persistence

The next eval comes back at **0.625** — a regression from the high-water mark of 0.709. The auto-rollback fires:

```
loop_end_cycle → {"outcome": "regressed", "delta": -0.084, "auto_rollback": {"result": "ok"}}
```

Boros hits two consecutive crashes during EVOLVE on cycles 18 and 19 — both automatically recovered with snapshot rollback. Cycle 20 ends with an empty reflection. Cycle 21 crashes again. None of this requires human intervention.

By cycle 22, Boros has identified a new angle: the `kernel` object passed to `memory_commit_archival` might be `None` in certain eval sandbox conditions, causing an `AttributeError` that the evaluator is logging as `ModuleNotFoundError`. It adds a safe fallback:

```python
# Before
boros_dir = str(kernel.boros_root) if kernel else os.getcwd()

# After
if kernel and hasattr(kernel, 'boros_root') and kernel.boros_root:
    boros_dir = str(kernel.boros_root)
else:
    boros_dir = os.getcwd()
```

Review board approves. Score after eval: **0.5** — still below high-water. Auto-rollback fires again. Boros records the cycle as a regression, archives the lesson, and starts cycle 23.

---

### What This Demonstrates

**The self-modification is real.** Boros reads its own Python files, writes diffs, and hot-reloads changed skills — no restart, no human in the loop.

**The review board is real.** A second LLM independently evaluates every proposed change. It rejected two proposals in this run for valid reasons. Boros adapted both times.

**The rollback is real.** Three separate auto-rollbacks happened across this run — all triggered automatically when scores dropped below the high-water mark.

**Failure is the signal.** Boros doesn't stop when a cycle fails. Each regression is archived as a lesson, referenced in the next REFLECT stage, and fed back into the next hypothesis. The system treats failure as data.

**Score progression across this run:**

| Cycle | Category | Score | Outcome |
|---|---|---|---|
| 14 | web_search | 0.333 | Baseline (diagnosed silent failure) |
| 15 | memory | 0.709 | **New high-water mark** |
| 17 | memory | 0.625 | Regressed — rolled back |
| 22 | memory | 0.500 | Regressed — rolled back |
| 23 | memory | evolving... | |

This is a system that genuinely improves itself, catches its own mistakes, and keeps going.
