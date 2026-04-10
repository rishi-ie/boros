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

## Environment Variables

```
# Required — at least one provider key
GEMINI_API_KEY=           # Default provider
ANTHROPIC_API_KEY=        # For Anthropic/Claude
OPENAI_API_KEY=           # For OpenAI

# Optional
TOGETHER_API_KEY=         # For Together.xyz (openai_compat provider)
```
