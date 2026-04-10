# Boros (ARES)

**A self-evolving AI that improves its own capabilities automatically.**

Boros runs an infinite loop where it rewrites its own internal skills, tests every change in an isolated sandbox, and rolls back anything that makes it worse. You configure what capabilities you want it to master — it figures out the rest.

---

## How It Works

Boros runs a 4-stage **Evolution Loop** continuously:

```
REFLECT → EVOLVE → VALIDATE → COMMIT
```

1. **REFLECT** — Reads its evaluation scores, finds its weakest capability, and forms a hypothesis for how to improve it.
2. **EVOLVE** — Targets the relevant skill and improves it. It always tries the safest approach first:
   - Modify the skill's behavioral rules (`SKILL.md`)
   - Add new Python functions to the skill
   - Create a brand new skill (last resort)
3. **VALIDATE** — An independent evaluator runs Boros on test tasks and scores its performance (0.0–1.0). If scores drop below the previous best, the change is automatically rolled back.
4. **COMMIT** — Approved changes are recorded in evolution history and loaded live — no restart needed.

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- At least one API key (Gemini is the default):
  - **Gemini**: `GEMINI_API_KEY` — [get one here](https://aistudio.google.com/app/apikey)
  - **Anthropic**: `ANTHROPIC_API_KEY`
  - **OpenAI**: `OPENAI_API_KEY`

### 2. Install

```bash
git clone <repo-url>
cd boros
pip install -r requirements.txt
```

### 3. Configure API Keys

```bash
cp .env.template .env
```

Open `.env` and fill in your key(s):

```
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
```

### 4. Configure the Provider (optional)

By default Boros uses Gemini 2.5 Flash. To switch providers, edit `config.json`:

```json
"providers": {
  "evolution_api": {"provider": "gemini", "model": "gemini-2.5-flash"},
  "meta_eval_api": {"provider": "gemini", "model": "gemini-2.5-flash"}
}
```

Supported providers: `gemini`, `anthropic`, `openai`, `ollama`, `openai_compat`.

### 5. Start

```bash
python start.py
```

This starts the eval-generator (the scoring sandbox) and then the kernel. At startup, you'll be prompted to choose a mode:

```
Select Boot Mode:
 1. Evolution Mode       (Autonomous self-improvement)
 2. Digital Employee Mode (Execution on demand)
```

- Choose **1** to let Boros run its evolution loop autonomously.
- Choose **2** to use Boros as an on-demand AI assistant that executes tasks you give it.

---

## Director Commands

Once running, you control Boros from the `director>` prompt:

| Command | What it does |
|---|---|
| `boros status` | Show the current cycle number, stage, and mode |
| `boros pause` | Pause the loop at the end of the current cycle |
| `boros resume` | Resume after a pause |
| `boros evolution` | Switch to Evolution Mode (self-improvement) |
| `boros employee` | Switch to Digital Employee Mode (task execution) |

Any other text you type starting with `boros ` is queued as a command for the agent to handle.

---

## Customizing What Boros Evolves

The `world_model.json` file is the only thing that controls what capabilities Boros targets. The current default is **Cognitive Memory** — teaching Boros to use its own memory system effectively.

To add your own capability, add an entry to `world_model.json`:

```json
{
  "categories": {
    "your_capability": {
      "name": "Human Readable Name",
      "description": "What this capability means in practice",
      "weight": 2.0,
      "related_skills": ["reasoning"],
      "anchors": [
        "Observable behavior the capability should exhibit",
        "Another observable behavior"
      ],
      "rubric": {
        "level_1": "Completely fails at this capability",
        "level_2": "Partial — works sometimes or in simple cases",
        "level_3": "Reliably functional",
        "level_4": "Full mastery — handles edge cases, consistent, optimal"
      },
      "failure_modes": [
        "Common way this capability breaks"
      ]
    }
  }
}
```

**Important:** `related_skills` must match directory names inside `skills/`. These are the skills Boros is allowed to modify when targeting this capability.

---

## Architecture Overview

```
kernel.py          — Config loading, skill registry, routing. Minimal by design.
agent_loop.py      — LLM ↔ tool dispatch engine. Runs each evolution cycle.
start.py           — Launches eval-generator + kernel together.
world_model.json   — Defines what capabilities to evolve toward.
config.json        — Provider settings, timeouts, eval parameters.
cycle_prompt.md    — Step-by-step instructions Boros follows each cycle.

skills/            — All intelligence lives here (15 skills)
eval-generator/    — Independent scoring sandbox (separate process)
memory/            — SQLite + JSONL persistent memory store
snapshots/         — Restorable skill snapshots (auto-managed)
session/           — Live loop state (cycle number, current stage, mode)
```

### Skills

Skills are the modular units of intelligence. Each skill has:
- `SKILL.md` — behavioral rules and instructions (what Boros edits most often)
- `functions/` — Python implementations
- `state/` — runtime state (persists between cycles)
- `tests/` — health checks

**Always-loaded skills:** `mode-controller`, `memory`, `skill-router`, `context-orchestration`, `reflection`, `meta-evolution`, `meta-evaluation`, `loop-orchestrator`

**Loaded on demand:** `reasoning`, `tool-use`, `web-research`, `eval-bridge`, `skill-forge`, `director-interface`, `eval_util`

### Evaluation Scores

Scores are 0.0–1.0, normalized from a 4-level rubric defined in `world_model.json`:

| Score | Meaning |
|---|---|
| 0.0–0.3 | Fundamental failure |
| 0.3–0.5 | Partial capability |
| 0.5–0.7 | Functional but weak |
| 0.7–0.9 | Strong |
| 0.9–1.0 | Near-mastery |

Every category has a **high-water mark** — the best score ever achieved. If a change drops any score below its high-water mark, Boros automatically rolls back to the previous snapshot.

---

## Boros in Action — Real Evolution Logs

The following is a real run. No edits, no cherry-picking. This is what Boros actually does when you start it.

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

---

## Environment Variables

```
# Required — at least one provider key
GEMINI_API_KEY=           # Default provider
ANTHROPIC_API_KEY=        # For Anthropic/Claude
OPENAI_API_KEY=           # For OpenAI

# Optional
TOGETHER_API_KEY=         # For Together.xyz (openai_compat provider)
```
