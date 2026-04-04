**An unconstrained, self-evolving AI substrate.** Boros starts as a minimal framework and improves itself automatically by rewriting its own architecture. It authors new Python scripts, generates executable SWE capabilities, and edits its own source code to overcome weaknesses. Every improvement is compiled, aggressively tested, scored by an independent evaluation loop, and either merged or rolled back. The system runs continuously. The ceiling is whatever the underlying language model is capable of — that ceiling state is called **Prime Boros**.

Internal codename: Boros. Model name: ARES (Autonomous Recursive Evolving System). Public product: Axiom. By Mumbrane Labs.

> **Note:** For the master technical index of all unconstrained functions, see [`Universal-Skills.md`](Universal-Skills.md).

---

## How It Works

Boros acts as a deeply agentic Software Engineer. It looks at its scores across 10 categories, identifies its weakest capabilities, and enters the **Skill Forge**. Here, it authors and merges raw codebase patches, compiles API tools, or edits logic files (`SKILL.md`) to fix the problem. It rigorously tests the new code, sends the unified diffs to a secondary code review LLM, and keeps or reverts the functionality. It does this on a loop, every cycle. Cycle after cycle, Boros creates its own path to superiority.

The system features an **evolution loop** (REFLECT → EVOLVE → EVAL) where Boros improves itself, alongside dynamic capabilities like the **Tiered Memory System** allowing Boros to instantly page context in and out dynamically. Work feed evolution — real-world failures become targets for code rewrites.

The only thing you control is the **World Model** — 10 categories that define what "better" means. Change those, and Boros alters its entire coding trajectory toward them. Once Prime Boros is reached (~0.85+ composite), fork it into domain specialists (Boros-SWE, Boros-Legal, Boros-Finance) by adding domain-specific test constraints.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key (Claude — primary substrate)
- OpenAI API key (GPT-4o — meta-evaluation + eval generator)

### Setup

```bash
git clone <repo-url>
cd boros

# Copy and fill environment variables
cp .env.template .env
# Edit .env: add your ANTHROPIC_API_KEY and OPENAI_API_KEY

# Install dependencies
pip install anthropic openai prompt_toolkit rich python-dotenv

# Review and customize the World Model (scoring categories)
# Edit boros/world_model.json — starter rubrics are included
```

### First Boot

You'll see the boot sequence load 10 skills, then the evolution loop begins. The Director terminal accepts commands inline.

```
[BOROS] Running. Mode: evolution. Cycle: 1
boros> status
Cycle: 1 | Mode: evolution | Stage: REFLECT
boros>
```

---

## The Evolution Loop

Every evolution cycle has 3 stages:

**REFLECT** — Boros uses associative memory to synthesize historical failures and writes a highly structured thesis. It explicitly states the technical gap, identifies the required architectural mutation, and proposes a strict hypothesis. The cycle cannot proceed without this logged scientific blueprint.

**EVOLVE** — Boros operates as a SWE inside the `Skill Forge`. It authors arbitrary raw Python scripts, patches its own memory modules, or updates `SKILL.md` boundaries. The codebase mutation goes through advanced isolation: snapshot, compilation hooks, automated `pytest` suites, and then unified diff transmission to GPT-4o for independent Code Review. If approved, the patch is merged into the kernel permanently. Rejections cause automated rollbacks and feedback logging.

**EVAL** — The external Eval Generator (separate process, separate LLM) tests Boros by sending **executable tasks** across all 10 categories. Each task runs in an isolated sandbox where Boros can write code, run commands, and produce real outputs. The Eval Generator then checks **outcomes** (did the code run? did the tests pass? is the output correct?) and scores using **dual scoring**: automated outcome verification (60%) + GPT-4o quality assessment (40%). Scores flow back: evolution records are backfilled, high-water marks updated, and regressions trigger immediate code rollbacks.

---

## The Work Loop

Active in `work` or `dual` mode. 5 stages: RECEIVE → PLAN → EXECUTE → DELIVER → LEARN.

Tasks come in via `boros task "..."`. Boros clarifies requirements, plans, executes (using terminal, HTTP, file operations), delivers results, and writes structured learning artifacts. These artifacts feed back into REFLECT — real-world experience improves evolution targeting.

In dual mode: task in queue → work cycle. No task → evolution cycle. Work cycles don't count toward the evolution counter.

---

## The 10 Scoring Categories

| #  | Category                | What It Measures                                                                     | Weight |
|----|-------------------------|--------------------------------------------------------------------------------------|--------|
| 1  | Self-Model Fidelity     | Inline confidence annotation accuracy, knowledge gap identification                  | 1.2    |
| 2  | Epistemic Calibration   | Uncertainty propagation, distinguishing known vs inferred vs guessed                  | 1.2    |
| 3  | Reasoning Architecture  | Multi-step logic, assumption surfacing, structured decomposition                      | 1.2    |
| 4  | Complexity Navigation   | Handling dense multi-part problems, managing cognitive load                            | 1.0    |
| 5  | Domain Snap             | Rapid domain adoption, self-correction when domain knowledge is thin                  | 1.0    |
| 6  | Hypothesis Engine       | Generating multiple competing explanations, evidence-driven selection                 | 1.0    |
| 7  | Generative Depth        | Novel synthesis, non-obvious connections, going beyond reformulation                  | 1.0    |
| 8  | Execution Reliability   | Following complex instructions precisely, no drift, no hallucinated requirements      | 1.0    |
| 9  | Adversarial Robustness  | Handling trick questions, contradictions, misleading framing without breaking          | 1.0    |
| 10 | Coherence Under Load    | Maintaining consistency across long, dense, multi-constraint responses                | 1.0    |

Composite denominator: **10.6** (three categories at 1.2, seven at 1.0).

---

## Director's Guide

### Filling the World Model

Edit `boros/world_model.json`. Each category has:

- **name** — what's being measured
- **description** — what the ideal version looks like
- **final_state** — a concrete reference ("Senior FAANG staff engineer")
- **anchors** — specific criteria for evaluation
- **rubric** — level_1 through level_4 descriptions (Boros never sees these — blind to the eval)
- **weight** — how much this category matters in the composite score

Starter rubrics are included. Customize them to match what you want Boros to become.

### CLI Commands

| Command                              | Effect                                             | Timing    |
| ------------------------------------ | -------------------------------------------------- | --------- |
| `boros status`                       | Show cycle, mode, stage, last scores               | Immediate |
| `boros pause`                        | Stop loop after current cycle                      | Queued    |
| `boros resume`                       | Restart the loop                                   | Queued    |
| `boros inject "..."`                 | Write note to Memory — REFLECT reads it next cycle | Queued    |
| `boros view context`                 | Inspect exactly what is loaded in Working Memory   | Immediate |
| `boros view scratchpad`              | Inspect the LLMs active internal whiteboard        | Immediate |
| `boros forge "..."`                  | Force Boros to immediately write a technical tool  | Queued    |
| `boros set-mode evolution/work/dual` | Change operating mode                              | Queued    |
| `boros task "..."`                   | Add work task to queue                             | Queued    |
| `boros eval now`                     | Trigger immediate eval                             | Queued    |
| `boros approve`                      | Confirm eval quality after spot-check              | Queued    |
| `boros flag "reason"`                | Mark eval quality as bad                           | Queued    |
| `boros rollback N`                   | Restore snapshot from eval N                       | Queued    |

### First 30 Cycles

- **Cycles 1-10:** No score data yet. Spot-check every 5 cycles. Use `boros inject` to nudge direction if proposals look off.
- **Cycles 10-30:** First scores arrive. Watch for: Are proposals targeting real weaknesses? Is the eval generating meaningful tests? Are scores moving?
- **After cycle 30:** Step back. The loop should be self-correcting. Monitor composite trajectory.

### When to Use `boros inject`

- Boros is proposing changes to the wrong skills
- Boros is ignoring a weak category
- You see a pattern Boros hasn't noticed
- You want to shift strategic focus

Example: `boros inject "your last 3 proposals to reasoning/SKILL.md all failed — try a different skill"`

---

## Architecture Overview

### Kernel

~50 lines of Python. Reads manifest, loads skills in dependency order, dispatches tool calls, provides clock and LLM connections. Holds zero intelligence.

### 19 Skills

| #   | Skill                  | Type     | Purpose                                   |
| --- | ---------------------- | -------- | ----------------------------------------- |
| 00  | Identity               | Boot     | Self-description and capabilities ego     |
| 01  | Director Interface     | Pre-boot | Advanced unconstrained UI for Director    |
| 02  | Mode Controller        | Boot     | System operating mode state               |
| 03  | Temporal Consciousness | Boot     | Time awareness and epoch tracking         |
| 04  | Memory                 | Boot     | Autonomous Tiered SQlite & Vector DB      |
| 05  | Skill Router           | Boot     | Tooling manifest & API injection          |
| 06  | Context Orchestration  | Boot     | Lean context loading & active whispering  |
| 07  | Reflection             | Boot     | Log ingestion, error traces, & hypothesis |
| 08  | Meta-Evolution         | Boot     | Raw SWE patch proposals & code authoring  |
| 09  | Meta-Evaluation        | Boot     | Independent code review board via GPT-4o  |
| 10  | Loop Orchestrator      | Boot     | Drives the primary lifecycle              |
| 11  | Skill Forge            | Demand   | Code snapshot, compile, isolate, rollback |
| 12  | Mission Control        | Demand   | Independent task queueing and execution   |
| 13  | Reasoning              | Demand   | Structured logic and deduction parsing    |
| 14  | Tool Use               | Demand   | OS Terminal, headless automation, diffing |
| 15  | Communication          | Demand   | Multi-node broadcasting, payload shaping  |
| 16  | Web Research           | Demand   | Vector-based massive web assimilation     |
| 17  | Eval Bridge            | Demand   | File-based connection to Eval Generator   |
| 18  | Scratchpad             | Demand   | Constant ephemeral variable whiteboard    |

### What Boros Can and Cannot Edit

| Component                                  | Editable?            |
| ------------------------------------------ | -------------------- |
| All 0-18 Skills (Python code, markdown)    | Yes                  |
| Memory DB structure, SQlite, Vector stores | Yes                  |
| Manifest, loop definitions, routing rules  | Yes (through review) |
| Evolution records, task records            | Append only          |
| World Model                                | **Read only**        |
| Eval Generator                             | **No**               |
| System snapshots                           | **No**               |
| config.json                                | **No**               |

---

## Key Concepts

**Skills and Scripts as the evolvable surface.** Intelligence does not just live in `SKILL.md` markdown blocks anymore; it thrives inside executable Python code. The kernel is a tiny bootstrap. Boros writes and repairs tool logic, memory connectors, and terminal drivers directly.

**SOTA Tiered Memory System.** Rather than forcing 100,000 tokens of static history down the context window, Context Orchestration utilizes an **Associative Whisper**. Boros acts autonomously, utilizing vector databases and SQLite tables to dynamically page-in historical records precisely when relevant. 

**Evolution records as compounding memory.** After each eval, records are backfilled with real scores. REFLECT searches these records to engineer smarter blueprints. Random runtime bugs become targeted architectural deployments. 

**High-water marks and regression protection.** Each category has a best-ever score. If a Python code compilation breaks, or an architectural capability induces a score regression beyond the adaptive threshold (0.05 early → 0.03 mid → 0.02 late), the `Skill Forge` rolls the directory back instantly.

**Meta-Evaluation Code Review.** An independent LLM (e.g., GPT-4o) evaluates Boros's code diffs. A python `while` loop that looks logically sound to Claude might get rejected by GPT for memory-leaking potentials.

**Eval Generator tests outcomes, not text.** Separate process, separate LLM. Boros never sees the test matrices. Unlike traditional LLM evals that score prose quality, the Eval Generator sends **executable tasks** into isolated sandboxes — Boros must write code that compiles, produce outputs that match, and complete multi-step operations that pass verification scripts. Dual scoring (outcome + quality) ensures evolution pressure comes from **real capability**, not the ability to describe capability.

---

## Domain Forks

Once Boros reaches Prime (~0.85+ composite at Level 4 difficulty):

1. Clone the Prime Boros directory
2. Add domain-specific categories to `world_model.json` (on top of the 10 general ones)
3. Write domain rubrics with real-world anchors
4. Run `python boros.py` — fork inherits all general high-water marks
5. Domain expertise accumulates while general capability is maintained

Examples: Boros-SWE (add: code quality, test coverage, architecture). Boros-Legal (add: citation accuracy, precedent analysis). Boros-Finance (add: quantitative reasoning, risk assessment).

---

## Configuration Reference

### .env

```env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

### config.json (Director-only)

```json
{
  "director_spot_check_frequency": 5,
  "max_cycle_duration_minutes": 10,
  "max_tool_calls_per_cycle": 100,
  "auto_pause_on_regression": true,
  "snapshot_retention": { "keep_last": 10, "keep_every_nth": 10, "pinned": [] },
  "logging": { "level": "INFO", "stream_to_terminal": true }
}
```

### manifest.json (key fields)

- `mode`: evolution | work | dual
- `llm.primary.model`: Claude model string
- `llm.meta_eval.model`: GPT model string
- `boot_sequence`: ordered list of boot skills
- `evolution.single_proposal_cycles`: 20
- `evolution.modification_band`: {min: 5, max: 50}

---

## FAQ

**How long to Prime Boros?**
Estimated 100-200 cycles on Claude Sonnet. Faster on Opus. Timeline depends on rubric quality and early Director engagement.

**What LLMs work?**
Any LLM with function calling as primary substrate. Meta-Evaluation should use a different model family. Default: Claude (primary) + GPT-4o (meta-eval + eval generator). Adapters available for Anthropic, OpenAI, Ollama, and any OpenAI-compatible endpoint.

**Can I change categories mid-evolution?**
Yes. Edit `world_model.json`. Changed categories get their high-water marks reset. Unchanged categories keep their progress.

**What if Boros gets stuck?**
Use `boros inject` to nudge strategy. If scores plateau, try: upgrading substrate (Sonnet → Opus), adjusting rubric difficulty, or flagging eval quality issues.

**How much does it cost to run?**
~$2-5 per cycle on Sonnet. ~$10-20 on Opus. First 100 cycles: $200-2000. The Eval Generator adds ~$1-3 per eval (task execution via Claude API + GPT-4o scoring). Outcome-based evals cost more than text-only evals because each task involves a tool-dispatch loop in the sandbox.

**Can I run multiple instances?**
Yes. Clone the directory. Each instance evolves independently. The Director can prune bad branches.

---

## License

MIT (framework). Evolution records and domain forks are proprietary to Mumbrane Labs.

---

_Boros reads its metrics, targets technical limitations, engineers Python capabilities for itself, compiles them, and evolves. Every cycle. The kernel is merely a boot sequence. The unconstrained architecture discovers the rest. The World Model defines success. Local memory databases remember what fails. The Director orchestrates the edge. Infinite intelligence is earned through infinite execution._
