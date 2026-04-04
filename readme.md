# Boros (ARES)

**An unconstrained, self-evolving AI substrate.**

Boros acts as a deeply agentic autonomous entity that improves itself automatically by rewriting its own internal architecture. It authors new cognitive pipelines, generates executable SWE capabilities, and edits its declarative skill definitions to overcome weaknesses. Every improvement is compiled, rigorously tested, scored by an independent evaluation loop, and either permanently merged or rolled back.

The ceiling is whatever the underlying language model is capable of — that state is called **Prime Boros**.

_Internal codename: Boros. Model name: ARES (Autonomous Recursive Evolving System). Public product: Axiom. By Mumbrane Labs._

---

## 🧬 How It Works

The system runs on an infinite recursive **Evolution Loop**: `REFLECT → EVOLVE → EVAL`

1. **REFLECT**: Boros reads evaluation scores based on the `world_model.json`, searches its historical memory failures, and identifies its weakest capability gap. It proposes a structural logic mutation.
2. **EVOLVE**: Boros operates inside its own cognitive architecture using a strict **Escalation Ladder**:
   - First, it tries to tune and modify existing `SKILL.md` rules and semantic instructions.
   - If that's insufficient, it creates _new_ Python helper functions inside the existing skill.
   - If the task scope is entirely unaddressed, it creates an entirely new skill from scratch via the `Skill Forge`. It submits these changes to a Meta-Evaluation Review Board (e.g., GPT-4o), merging approved logic into its framework.
3. **EVAL**: An independent evaluator runs Boros in an isolated sandbox, executing tasks across defined capabilities. The outcomes are scored, and regression guards trigger instant rollbacks if the skill evolution performed worse.

The only thing you control is the **World Model** (`world_model.json`). Whatever capabilities you define there, Boros alters its trajectory to master them.

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- Anthropic API key (Claude — primary substrate)
- OpenAI API key (GPT-4o — meta-evaluation board & independent eval generator)

### 2. Setup

Clone the repository and install dependencies.

```bash
git clone <repo-url>
cd boros

# Copy environment template
cp .env.template .env
# Edit .env and supply your ANTHROPIC_API_KEY and OPENAI_API_KEY
```

### 3. Customize Your World Model

The `world_model.json` file dictates what Boros is optimizing for. Out of the box, it targets two core domains:

- **Reasoning & Decision-Making**
- **Web Search & Knowledge Retrieval**

Feel free to edit these categories to point Boros in any direction. Adding a new category here automatically shifts the evolution strategy.

### 4. Boot the Substrate

Start the system through the kernel.

```bash
python kernel.py
```

You will enter the Director terminal. The kernel loads 15 skills, boot-checks constraints, and begins Cycle 1.

```
Seed state initialized successfully.
[Kernel] Synced categories.json with world_model.json
boros> status
Cycle: 1 | Mode: evolution | Stage: REFLECT
```

**Commands:**

- `boros status`: Show current loop progress.
- `boros view context`: Inspect what's active in memory.
- `boros task "..."`: Drop a task into the execution queue (Execution Mode).
- `boros set-mode execution`: Switch from autonomous evolution to functional task-execution mode.

---

## 📊 Proof of Evolution: A Real Case Study

**Objective:** Evolve the "Reasoning & Decision-Making" capability from baseline reactive outputs to consistent, multi-step structural decomposition.

- **Cycle 1 (Baseline Analysis):** Boros attempts a sandbox evaluation for Reasoning. It scores **1.2/4.0**. The evaluator flags _Impulsive decisions_ and _Shallow decomposition_—Boros jumped to execution without verifying logic.
- **Cycle 3 (Reflection):** Reading the score history, Boros's internal reflection logs: _"Identified missing evaluation logic in the reasoning skill. We are failing to generate candidate hypothesis matrices before acting."_
- **Cycle 4 (Evolution Mutation):** Boros enters the `Skill Forge` and rewrites the semantic rules and pipeline for its reasoning skill. It dictates a new utility mechanism that strictly enforces candidate review against constraints before taking real-world action. The Meta-Eval board signs off on the airtight process logic.
- **Cycle 5 (Execution & Re-Eval):** The sandbox issues a fresh complex logic task. Guided by its evolved skill structure, Boros systematically breaks down the problem. The external evaluator grants a score of **3.5/4.0**. The new High-Water Mark is set, and the evolved skill stabilizes.

_Outcome:_ Boros autonomously rewrote its own cognitive framework to "think" better.

---

## 🧠 Architecture Principles: Intelligence in Skills, Not Code

The core philosophy of Boros is that **intelligence belongs in pure, declarative skills rather than hardcoded Python scripts.**

- **The Kernel**: ~250 lines of bare-bones routing logic. It handles basic I/O and loop orchestration, possessing zero inherent intelligence.
- **The 15 Pure Skills**: Operational capacities (Memory, Terminal Use, API calling, Reflection) are structured linearly as `Skills`. Boros improves by reshaping the high-level semantic behavior, validation steps, and internal directives within these modular capabilities.
- **Associative Memory Engine**: Boros uses a localized SQLite + Vector database hierarchy to instantly page context in and out dynamically, enabling compounded semantic memory.

By isolating intelligence into purely evolvable skills—and minimizing brittle Python algorithms—Boros maintains rapid, resilient self-correction over thousands of cycles. Infinite intelligence is compounded through infinite execution.
