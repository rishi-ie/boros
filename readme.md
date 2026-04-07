# Boros (ARES)

**An open-source, self-evolving AI substrate.**

Boros autonomously improves its own capabilities by rewriting its internal skill architecture, testing every change in an isolated sandbox, and rolling back anything that regresses. The only thing you configure is the **World Model** — a JSON file that defines what capabilities Boros should master. Everything else is automatic.

> Internal codename: Boros. Model name: ARES (Autonomous Recursive Evolving System). By Mumbrane Labs.

---

## How It Works

Boros runs an infinite **Evolution Loop**:

```
REFLECT → EVOLVE → VALIDATE → COMMIT
```

1. **REFLECT** — Reads evaluation scores, identifies the weakest capability from the World Model, analyzes score history, and forms an improvement hypothesis.
2. **EVOLVE** — Targets the relevant skill and improves it following a strict escalation ladder:
   - First: modify the skill's `SKILL.md` semantic rules (fastest, safest)
   - Second: add new Python functions inside the skill
   - Third: create an entirely new skill from scratch
3. **VALIDATE** — An independent eval-generator runs Boros on sandbox tasks and scores its performance (0.0–1.0, graded against each capability's rubric). Regression against the high-water mark triggers automatic rollback.
4. **COMMIT** — Approved improvements are committed to evolution records and loaded live without restarting.

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- At least one API key:
  - **Gemini** (default): `GEMINI_API_KEY`
  - **Anthropic**: `ANTHROPIC_API_KEY`
  - **OpenAI**: `OPENAI_API_KEY`

### 2. Setup

```bash
git clone <repo-url>
cd boros
pip install -r requirements.txt

cp .env.template .env
# Edit .env and add your API keys
```

### 3. Configure the World Model

Edit `world_model.json` to define what Boros should evolve toward. See `world_model.examples/` for ready-made configurations (coding, research, reasoning).

The default world model targets **Reasoning** and **Web Search**. To change what Boros evolves, simply edit this file — it's picked up on every cycle automatically.

### 4. Start Boros

```bash
python run.py
```

This starts both the kernel and the eval-generator together. You'll enter the **Director terminal**.

**Director commands:**
- `boros status` — show current cycle, stage, and mode
- `boros view context` — inspect active memory and scores
- `boros task "..."` — submit a task (switches to Execution Mode)
- `boros set-mode execution` — switch to task execution mode
- `boros set-mode evolution` — switch back to self-evolution mode

### 5. (Optional) Docker

```bash
docker-compose up
```

---

## Customizing the World Model

The `world_model.json` file is the only thing that controls what Boros evolves toward. Add any capability you want:

```json
{
  "categories": {
    "your_capability": {
      "name": "Human Readable Name",
      "description": "What this capability means",
      "anchors": ["Observable behavior 1", "Observable behavior 2"],
      "rubric": {
        "level_1": "Baseline / failure",
        "level_2": "Partial capability",
        "level_3": "Functional",
        "level_4": "Full mastery"
      },
      "failure_modes": ["Common failure 1", "Common failure 2"],
      "related_skills": ["reasoning"],
      "weight": 2.0
    }
  }
}
```

**`related_skills` must match directory names in `skills/`.**

See `world_model.examples/` for complete working examples.

---

## Architecture

### The Kernel (250 lines)
`kernel.py` is intentionally minimal: config loading, skill registration, and routing. Zero intelligence lives here.

### 15 Modular Skills
Intelligence lives in skills. Each skill has:
- `SKILL.md` — behavioral rules and semantic instructions (primary evolution target)
- `functions/` — Python implementations
- `state/` — persistent runtime state
- `tests/` — health checks

**Boot skills** (always loaded): `mode-controller`, `memory`, `skill-router`, `context-orchestration`, `reflection`, `meta-evolution`, `meta-evaluation`, `loop-orchestrator`

**Demand skills** (loaded when needed): `reasoning`, `tool-use`, `web-research`, `eval-bridge`, `skill-forge`, `director-interface`, `eval_util`

### The Eval Generator
A separate process (`eval-generator/eval_generator.py`) that:
1. Generates tasks from world model rubrics and anchors
2. Runs Boros in an isolated sandbox with tool access
3. Grades output using deterministic checks + LLM rubric scoring
4. Returns scores to the main loop

`run.py` starts both processes together and manages their lifecycle.

### Memory
- **File store**: JSON files in `memory/experiences/`, `memory/evolution_records/`
- **SQLite + FTS5**: `memory/memory.db` for fast full-text search across all archived experiences
- **Score history**: `memory/score_history.jsonl` — append-only log of every eval result

---

## Environment Variables

```
# Required (pick at least one)
GEMINI_API_KEY=         # For Gemini provider (default)
ANTHROPIC_API_KEY=      # For Anthropic/Claude provider
OPENAI_API_KEY=         # For OpenAI provider

# Optional
TOGETHER_API_KEY=       # For Together.xyz (openai_compat provider)
```

Configure which provider drives evolution and meta-evaluation in `config.json`:

```json
"providers": {
  "evolution_api": {"provider": "gemini", "model": "gemini-2.5-flash"},
  "meta_eval_api": {"provider": "gemini", "model": "gemini-2.5-flash"}
}
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add world model categories, new skills, and LLM adapters.

---

## License

MIT — see [LICENSE](LICENSE).
