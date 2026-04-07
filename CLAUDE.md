# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

**Boros (ARES)** — an Autonomous Recursive Evolving System. It runs an infinite self-improvement loop where it rewrites its own skills, tests the changes in a sandbox evaluator, and rolls back on regression. The system is a meta-AI that improves itself rather than solving external tasks directly (though it supports a "work" mode for that).

## Running the System

```bash
# Setup (first time)
cp .env.template .env
# Fill in ANTHROPIC_API_KEY, GEMINI_API_KEY (required), OPENAI_API_KEY (optional)
pip install -r requirements.txt

# Start
python kernel.py
```

The Director terminal UI launches automatically. Key commands:
- `boros status` — show cycle/stage/mode
- `boros view context` — inspect active memory
- `boros task "..."` — submit an execution task
- `boros set-mode evolution|work|dual` — switch modes

## Architecture

### The Core Loop

`kernel.py` (~250 lines) is intentionally dumb — just config loading, skill registration, and routing. All intelligence lives in 15 modular skills.

`agent_loop.py` is the LLM ↔ tool dispatch engine. Each cycle it:
1. Builds a dynamic system prompt from BOROS.md + loop state + world model + scores
2. Sends to the configured LLM (default: Gemini 2.5 Flash for evolution)
3. Dispatches tool calls to the kernel registry
4. Loops until the LLM stops or limits hit (100 tool calls, 10 min timeout)

The 4-stage evolution cycle (defined in `cycle_prompt.md`):
- **REFLECT** — read scores, find weakest capability gap
- **EVOLVE** — modify or create skills (see escalation ladder below)
- **VALIDATE** — sandbox eval scores the change (0–4 scale)
- **COMMIT** — merge if improved, rollback if regressed

### Skill Architecture

Every skill lives in `skills/{name}/` and contains:
- `SKILL.md` — the semantic role and behavioral rules (primary evolution target)
- `skill.json` — metadata, version, dependencies
- `functions/` — Python implementations
- `state/` — runtime state (git-ignored)
- `tests/test_basic.py` — minimal health check

Boot-order skills (loaded at startup): `mode-controller → memory → skill-router → context-orchestration → reflection → meta-evolution → meta-evaluation → loop-orchestrator`

Demand skills (loaded when needed): `reasoning`, `tool-use`, `web-research`, `eval-bridge`, `skill-forge`, `director-interface`, `eval_util`

### Evolution Escalation Ladder

When improving a capability, always follow this order:
1. Modify `SKILL.md` semantic rules (preferred — no code change)
2. Add/modify Python helper functions in `functions/`
3. Create an entirely new skill via Skill Forge (last resort)

**Never** repeatedly rewrite the same code. **Never** touch infrastructure skills (kernel, agent_loop, adapters) during evolution.

### Evaluation System

`eval-generator/` is an independent sandbox that:
- Generates executable tasks per world model category
- Scores Boros performance (0–4 scale)
- Feeds scores back to trigger evolution targets

`world_model.json` defines the evolution trajectory — currently two categories: `reasoning` (weight 2.5) and `web_search` (weight 2.0). Each has anchors, rubrics, failure modes, and `related_skills` that evolution is allowed to target.

A **meta-evaluation review board** (secondary LLM) independently validates proposals before they're committed.

### LLM Providers

`adapters/providers/` supports: `anthropic`, `gemini`, `openai`, `ollama`, `openai_compat`

Configured in `config.json`:
- `evolution_api` — drives the main loop (default: Gemini 2.5 Flash)
- `meta_eval_api` — independent review (default: Gemini 2.5 Flash)

### State (all git-ignored)

- `session/` — loop state, active hypothesis, current cycle
- `evals/` — scores, category definitions
- `memory/` — SQLite + vector index, score history JSONL
- `snapshots/` — restorable skill snapshots (keeps last 10, every 10th)
- `tasks/` — queue/active/completed task state

## Windows Path Conventions

This codebase runs on Windows. Inside any skill code or shell commands, use:
- `type` instead of `cat`, `dir` instead of `ls`
- Backslashes in file paths (`skills\reasoning\functions\`)
- Do not use POSIX-only commands

## Key Invariants

- `kernel.py` stays small — routing only, no intelligence
- Skills hot-reload via `kernel.reload_skill()` without restart
- `auto_pause_on_regression: true` in config — any score drop triggers automatic rollback
- The system is self-modifying: changes you make to skills may be overwritten by the evolution loop
