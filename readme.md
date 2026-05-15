# Boros

Self-evolving AI agent that modifies its own Python capabilities, tests changes in an isolated sandbox, and rolls back anything that decreases performance.

No fixed prompts. No logic trees. Boros reads its world model, proposes code changes, gets evaluated by an independent review board, and commits or rolls back automatically.

---

## How It Works

Boros runs an endless loop of **Reflect → Evolve → Validate → Commit/Rollback**:

1. **Reflect** — reads logs, scores, past failures to form a hypothesis
2. **Evolve** — edits its own Python files or `SKILL.md` instructions
3. **Validate** — independent evaluator scores it 0.0–1.0 on generated test scenarios
4. **Commit** — score beats high-water mark → code stays, hot-reloaded
5. **Rollback** — score drops → snapshot restore, changes erased

A second LLM (the review board) independently approves or rejects every proposal. Boros can't approve its own changes.

---

## Setup

### Requirements

- Python 3.11+
- API key: `MINIMAX_API_KEY` (primary), `GEMINI_API_KEY` (fallback)

### Install

```bash
git clone <repo-url>
cd boros

# Create env file
cp .env.template .env
# Edit .env, add: MINIMAX_API_KEY=your_key_here

# Install
pip install -e .
```

### Run

```bash
python start.py
```

---

## The Interface

On startup you see:

```
██████╗  ██████╗ ██████╗  ██████╗ ███████╗
██████╔╝██║   ██║██████╔╝██║   ██║███████╗
██╔══██╗██║   ██║██╔══██╗██║   ██║╚════██║
██████╔╝╚██████╔╝██║  ██║╚██████╔╝███████║
╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝

  self-evolving agent  ·  ARES
  loading...

  LLM ready  ·  MiniMax-M2.7
  16 skills loaded

  ● ready  ·  minimax  ·  16 skills
  /help for commands  ·  type naturally to evolve

boros > _
```

The agent loop starts immediately. Type naturally to give it a goal, or use slash commands.

---

## Commands

Type at the `boros>` prompt:

### Core
| Command | Alias | What it does |
|---|---|---|
| `/status` | `s` | Show full dashboard with scores, agents, meta, version |
| `/pause` | `p` | Pause after current cycle |
| `/resume` | `r` | Resume from pause |

### Lifecycle
| Command | Alias | What it does |
|---|---|---|
| `/evolve` | `e` | Switch to evolution mode |
| `/work` | `w` | Switch to work mode (task execution only) |
| `/fork` | | Fork as deployment agent (freezes evolution) |
| `/revolve` | `rev` | Resume evolution from fork |
| `/snap [label]` | | Create a manual snapshot |

### Info
| Command | Alias | What it does |
|---|---|---|
| `/scores` | `sc` | Show all capability scores with bars |
| `/skills` | `sk` | List all skills and their function counts |
| `/logs` | `l` | Tail recent logs (default last 10) |
| `/logs 20` | | Tail last 20 logs |
| `/who` | | Show identity / persona info |
| `/env` | | Show model, provider, skills, functions, cycle |
| `/cycles` | | Show cycle count, mode, generation |
| `/help` | `h` | Show this help |

### System
| Command | Alias | What it does |
|---|---|---|
| `/clear` | | Clear screen |
| `/quit` | `q` | Exit |

### Natural Language

Anything **without** a leading `/` is treated as an evolution goal. Boros queues it and runs an evolution cycle focused on that goal.

```
boros > improve memory recall
  ◉ queued: improve memory recall...
  running evolution cycle...

boros > make web search more reliable
  ◉ queued: make web search more reliable...
  running evolution cycle...
```

---

## Architecture

```
start.py          — boot: logo, kernel, eval engine, hand off to CLI
kernel.py         — registry, skills, LLM adapters, config
agent_loop.py     — the evolution engine (Reflect→Evolve→Validate)
skills/           — the live codebase Boros modifies
  director_interface/ — the CLI you interact with
  eval-bridge/    — scoring bridge to evaluator
  meta-evolution/ — the mutation engine
  memory/         — episodic memory
  reflection/     — hypothesis generation
  skill-forge/    — create new skills
  world_model/    — goals and rubrics
eval-generator/   — isolated scoring sandbox (separate process)
version_control/  — snapshot management
agents/           — multi-agent sub-system (reflector, architect, reviewer)
```

### Key Files

- `world_model.json` — goals, rubrics, milestones. Edit this to steer Boros's trajectory.
- `config.json` — provider priority, model selection, LLM settings.
- `manifest.json` — registry of all skills and their provided functions.
- `session/loop_state.json` — current mode, cycle, generation. Written by agent loop.
- `skills/eval-bridge/state/high_water_marks.json` — best scores achieved.
- `logs/cycles.log` — all cycle events and outcomes.
- `snapshots/` — auto-saved copies of `skills/` directory.

---

## The World Model

Boros is governed by `world_model.json`, not hardcoded directives. To change what Boros optimizes for, edit the world model:

```json
{
  "categories": {
    "reasoning": {
      "name": "Logical Problem Solving",
      "weight": 5.0,
      "rubric": {
        "level_1": "Fails basic logical deduction",
        "level_2": "Solves single-step problems",
        "level_3": "Handles multi-step chains with errors",
        "level_4": "Robust multi-hop reasoning"
      }
    }
  }
}
```

Boros clears milestones by beating score thresholds. The evaluator (`eval_check_milestone`) reads the world model to decide which difficulty tier to test next.

---

## Modes

**Evolution mode** (default) — Boros continuously reflects, proposes changes, and runs evaluation cycles. The agent loop never stops unless paused or forked.

**Work mode** (`/work`) — Boros operates as a task executor. No self-modification. Waits for tasks in `commands/pending.json`.

**Forked mode** (`/fork`) — Evolution frozen. Boros becomes a deployment agent (`boros-fork`). Generation incremented in `lineage.json`. When ready, `/revolve` resumes evolution.

---

## Safety

- **Review board**: every proposal is evaluated by an independent LLM with no context of the evolution loop
- **Auto-rollback**: if composite score drops below high-water mark, the last snapshot is restored automatically
- **No human required**: the loop runs, fails, adapts, and recovers without intervention
- **Failures are data**: each regression is archived as a lesson and fed back into the next reflection

---

## Dependencies

```
pip install -e .
```

Only standard library + your API key. No Rich, no Textual — pure ANSI escape codes for the CLI.

---

## Quick Reference

```bash
python start.py              # start
python start.py --mode work # start in work mode
Ctrl+C                      # graceful exit
```