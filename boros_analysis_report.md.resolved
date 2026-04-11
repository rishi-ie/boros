# Boros — Complete Project Analysis Report

> **Generated**: 2026-04-11 · **Scope**: Every file in the repository · **Source**: `rishi-ie/boros` (fresh clone)

---

## 1. Executive Summary

**Boros** is an **Autonomous Recursive Evolving System (ARES)** — an AI agent that **reads its own Python source code, rewrites it, tests the changes in an isolated sandbox, and rolls back any mutation that causes a performance regression**. It does this in a continuous loop with zero human intervention.

The system's ultimate objective is to reach a state called **"Prime Boros"**, where every capability defined in its World Model scores at Level 4 (mastery) consistently.

### Key Architectural Properties

| Property | Description |
|---|---|
| **Self-Modifying** | Boros edits its own Python files and reloads them live without restarting |
| **Self-Evaluating** | An independent eval sandbox (separate process) generates adversarial tasks and grades performance |
| **Self-Correcting** | Automatic rollback restores code when scores regress below the high-water mark |
| **Self-Aware** | A knowledge graph and evolution ledger record every mutation and its score impact |
| **Multi-Modal LLM** | Supports Gemini, Anthropic, OpenAI, Ollama, and any OpenAI-compatible API simultaneously |
| **Deployable** | Fork mechanism freezes evolution into a stable "employee" agent for production use |

---

## 2. Project File Map

```
boros/
├── start.py                    # Entry point — boots kernel, launches eval-generator, opens CLI
├── kernel.py                   # BorosKernel — registry, config, manifest, skill loading
├── agent_loop.py               # LLM ↔ Tool dispatch engine (evolution + execution cycles)
├── adapt_engine.py             # Field adaptation engine (used during boros-fork state)
├── tool_schemas.py             # Centralized tool schema definitions (Anthropic format)
├── BOROS.md                    # System identity prompt (injected into every LLM call)
├── cycle_prompt.md             # Per-cycle evolution instructions (the "user" message)
├── config.json                 # Runtime configuration (LLM providers, limits, eval settings)
├── manifest.json               # Skill registry, boot order, function declarations
├── world_model.json            # Capability rubrics, milestones, scoring targets
├── lineage.json                # Fork/re-evolve generational history
├── requirements.txt            # Python dependencies
├── .env.template               # API key template
│
├── adapters/                   # LLM Provider Abstraction Layer
│   ├── base_adapter.py         # Abstract interface: complete(), stream(), supports_tools
│   └── providers/
│       ├── gemini.py           # Google Gemini (REST API, no SDK dependency)
│       ├── openai.py           # OpenAI GPT-4o (official SDK)
│       ├── anthropic.py        # Anthropic Claude (official SDK)
│       ├── ollama.py           # Local Ollama (no tools, text-only)
│       └── openai_compat.py    # Together/Groq/etc (OpenAI-compatible endpoints)
│
├── eval-generator/             # Isolated Evaluation Sandbox (separate process)
│   ├── eval_generator.py       # Task generation, agent execution, grading pipeline
│   └── tool_dispatcher.py      # Sandboxed tool execution with path traversal protection
│
├── evals/
│   └── categories.json         # Synced from world_model.json at boot
│
└── skills/                     # 15 modular skill directories (the "brain")
    ├── context-orchestration/   # Context loading and manifest management
    ├── director-interface/      # Rich CLI (boros> prompt, fork/re-evolve commands)
    ├── eval-bridge/             # Score reading, regression checking, milestone tracking
    ├── eval_util/               # Evaluation artifact generation
    ├── loop-orchestrator/       # Cycle lifecycle (start/advance/end), ledger writes
    ├── memory/                  # Episodic/semantic memory, knowledge graph, SQL search
    ├── meta-evaluation/         # Independent review board (second LLM reviews code diffs)
    ├── meta-evolution/          # Code mutation engine (orient/propose/apply/rollback)
    ├── mode-controller/         # Operating mode state machine
    ├── reasoning/               # Structured reasoning (decompose, evaluate, plan)
    ├── reflection/              # Score analysis, hypothesis generation
    ├── skill-forge/             # File editing, snapshotting, validation, new skill creation
    ├── skill-router/            # Tool manifest, budget tracking
    ├── tool-use/                # Terminal, file I/O, path guard safety
    └── web-research/            # DuckDuckGo search, URL browsing, archival
```

---

## 3. Boot Sequence

```mermaid
sequenceDiagram
    participant User
    participant start.py
    participant EvalGenerator
    participant BorosKernel
    participant DirectorInterface

    User->>start.py: python start.py
    start.py->>EvalGenerator: subprocess.Popen(eval_generator.py)
    Note over EvalGenerator: Writes .ready file when initialized
    start.py->>start.py: Wait for .ready (up to 30s)
    start.py->>BorosKernel: BorosKernel()
    BorosKernel->>BorosKernel: _load_config() → config.json
    BorosKernel->>BorosKernel: _load_manifest() → manifest.json
    BorosKernel->>BorosKernel: _validate_world_model() → world_model.json
    BorosKernel->>BorosKernel: _check_first_boot() → creates session/, snapshots/, etc.
    BorosKernel->>BorosKernel: _sync_world_model_state() → syncs categories + high_water_marks
    BorosKernel->>BorosKernel: _load_skills() → imports all 15 skill modules
    BorosKernel->>BorosKernel: load_adapter(evolution_api) → e.g. GeminiAdapter
    BorosKernel->>BorosKernel: load_adapter(meta_eval_api) → e.g. GeminiAdapter
    start.py->>start.py: Ping LLM ("ping" → "pong")
    start.py->>DirectorInterface: DirectorInterface(kernel).run()
    DirectorInterface->>User: Mode selection (evolve/work) or resume
    DirectorInterface->>DirectorInterface: threading.Thread(run_kernel_loop)
    DirectorInterface->>User: boros> prompt (command loop)
```

### First Boot

On first boot (`session/current_cycle.json` doesn't exist), the kernel:
1. Creates all runtime directories: `session/`, `tasks/`, `snapshots/`, `evals/scores/`, `commands/`, `memory/`
2. Seeds `evals/categories.json` from `world_model.json`
3. Seeds `skills/eval-bridge/state/high_water_marks.json` with `{category: 0.0}`
4. Seeds `session/loop_state.json` with `{cycle: 0, stage: null, mode: "evolution"}`
5. Seeds `commands/pending.json` with `{pending: []}`

### Every Boot

Regardless of first boot, `_sync_world_model_state()` runs to ensure:
- New world model categories get added to `categories.json` and `high_water_marks.json`
- Removed categories get cleaned up from both files
- This means you can hot-edit `world_model.json` between runs and it propagates automatically

---

## 4. The Core Evolution Loop (4 Stages)

This is the heart of the system. Every evolution cycle follows:

```mermaid
graph LR
    A["🔍 REFLECT"] --> B["🧬 EVOLVE"]
    B --> C["🧪 VALIDATE"]
    C --> D["📝 COMMIT"]
    D --> A
    
    style A fill:#4a90d9,color:#fff
    style B fill:#e67e22,color:#fff
    style C fill:#27ae60,color:#fff
    style D fill:#8e44ad,color:#fff
```

### Stage 1: REFLECT

**Purpose**: Understand current state, identify weaknesses, form a hypothesis.

| Step | Tool Call | What It Does |
|---|---|---|
| 1 | `loop_start` | Increments cycle counter, sets stage to REFLECT |
| 2 | `eval_read_scores` | Reads latest evaluation results from eval-generator |
| 3 | — | Agent reads `scoring_breakdown` for root cause diagnosis |
| 4 | `evolve_history` | Reads past evolution attempts |
| 5 | `evolve_query_ledger(mode="regressions")` | Gets failed approaches to avoid repeating |
| 6 | `reflection_analyze_trace` | Statistical analysis of score trends |
| 7 | `evolve_orient` | UCB1-inspired targeting: finds weakest category + best candidate files |
| 8 | `reflection_write_hypothesis` | Records the improvement plan |
| 9 | `loop_advance_stage` | Transitions to EVOLVE |

**Key insight**: `evolve_orient` uses a **UCB1 (Upper Confidence Bound)** algorithm to balance:
- **Exploitation**: targeting the weakest-scoring category
- **Exploration**: preferring rarely-targeted skills over frequently-targeted ones

### Stage 2: EVOLVE

**Purpose**: Modify the codebase to improve a specific capability.

The **Escalation Ladder** (ordered by risk):
1. **Modify SKILL.md** — Change behavioral instructions (safest, fastest)
2. **Add/edit Python functions** — Fix bugs, add logic (medium risk)
3. **Create new skill** — Scaffold entirely new capability (highest risk)

| Step | Tool Call | What It Does |
|---|---|---|
| 1 | `evolve_set_target` | Declares what skill/file will be changed |
| 2 | `forge_snapshot` | Creates a restorable snapshot before modification |
| 3 | `tool_terminal` | Reads actual code files to understand current state |
| 4 | Various | `forge_edit_skill_md`, `tool_file_edit_diff`, `tool_file_write`, or `forge_create_skill` |
| 5 | `forge_validate` | Syntax-checks modified Python files |
| 6 | `forge_test_suite` | Runs tests if they exist |
| 7 | `evolve_propose` | Packages the change + validates against anti-brute-force |
| 8 | `review_proposal` | Sends to independent Review Board (second LLM) |
| 9 | `evolve_apply` (if approved) | Commits proposal + hot-reloads the modified skill |

**Anti-brute-force mechanism**: `evolve_propose` checks the evolution ledger. If the same file has been modified 2+ times recently without improvement, the proposal is **blocked automatically**. This prevents the LLM from endlessly retrying the same failing approach.

### Stage 3: VALIDATE

**Purpose**: Test the modified code against fresh, adversarial evaluation tasks.

| Step | Tool Call | What It Does |
|---|---|---|
| 1 | `eval_request` | Sends evaluation request to the eval-generator subprocess |
| 2 | `eval_read_scores(eval_id=...)` | Polls for results (blocks up to 5 minutes) |
| 3 | `eval_check_regression` | Compares new scores against high-water marks |

If scores **regressed**: automatic rollback is triggered via `forge_rollback`, restoring the snapshot created in EVOLVE.

### Stage 4: COMMIT

**Purpose**: Record what happened for institutional memory.

| Step | Tool Call | What It Does |
|---|---|---|
| 1 | `memory_commit_archival` | Records lesson/observation to long-term memory |
| 2 | `loop_end_cycle` | Finalizes everything (see below) |

**`loop_end_cycle` does 8 things automatically:**
1. Computes score delta (before vs. after)
2. Determines outcome: improved / regressed / neutral / baseline
3. Reads auto-rollback status from `eval_check_regression`
4. Writes to the **evolution ledger** (append-only JSONL)
5. Writes **knowledge graph triples** (score, modification, causal links)
6. Archives the hypothesis with outcome data
7. Updates **high-water marks** via `eval_update_high_water`
8. Checks for **milestone advancement** via `eval_check_milestone`
9. Cleans up session artifacts

---

## 5. The Evaluation Pipeline (eval-generator)

The eval-generator runs as a **separate subprocess**, completely isolated from the evolution engine. This prevents the agent from gaming its own tests.

```mermaid
graph TD
    A["eval_request (skill)"] -->|writes req.json| B["shared/requests/"]
    B --> C["EvalGenerator._poll_requests()"]
    C --> D["For each category:"]
    D --> E["_generate_task() → LLM creates adversarial task"]
    E --> F["_run_single_task() → Actor LLM executes task in sandbox"]
    F --> G["_grade_sandbox() → 3-layer grading"]
    G --> H["shared/results/eval-xxx.json"]
    H -->|polled by| I["eval_read_scores (skill)"]
    
    style A fill:#3498db,color:#fff
    style G fill:#e74c3c,color:#fff
    style H fill:#27ae60,color:#fff
```

### 3-Layer Grading System

| Layer | Type | What It Checks |
|---|---|---|
| **Layer 1** | Deterministic | Hard fail: no files + final error = score 0.0 |
| **Layer 2** | Deterministic | Outcome score: +0.5 for meaningful files, +0.25 for domain tools, +0.25 for success status |
| **Layer 3** | LLM | Quality score: grade against world model rubric (Level 1–4), normalize to 0.0–1.0 |

**Final score**: `composite = outcome_score × 0.5 + quality_score × 0.5` (blended, difficulty-weighted)

### Multi-Task Averaging

Each category runs **N tasks** (default 3, configurable via `eval_tasks_per_category`). Scores are averaged across all runs to reduce variance.

### Sandbox Security

The `ToolDispatcher` in the eval sandbox:
- **Path traversal protection**: `_safe_path()` prevents escape from sandbox directory
- **Blocked prefixes**: `identity_`, `loop_`, `evolve_`, `eval_`, `forge_`, `mission_`, `comm_`, `router_` — core infra tools are blocked inside the sandbox
- **Command timeout**: 30-second subprocess timeout
- Each category gets its own **isolated BorosKernel instance** to prevent state leakage

---

## 6. The Review Board (Meta-Evaluation)

Every code change must pass an **independent review** by a second LLM (the `meta_eval_api`). This LLM has no context about the evolution loop — it evaluates the diff purely on its technical merits.

**Review criteria:**
1. **Correctness** — Will the code run without errors?
2. **Improvement** — Does it genuinely improve the function?
3. **Safety** — Could it break other parts of the system?
4. **Python syntax** — Is it valid Python?
5. **Algorithmic depth** — Does it modify control flow, algorithms, or structural capability?

**Critical rejection rule**: Any proposal that ONLY changes string phrasing, comments, prompts, or docstrings is **automatically rejected** as cosmetic.

**Verdicts:**
| Verdict | Effect |
|---|---|
| `apply` | Code is committed and hot-reloaded |
| `reject` | Code is rolled back via snapshot; proposal is dead |
| `modify` | Code is rolled back; feedback written to `session/review_feedback.json`; up to 2 revisions allowed |

**Fallback**: If the meta-eval LLM is unavailable, the default verdict is **REJECT** (fail-closed, not fail-open).

---

## 7. The World Model

[world_model.json](file:///e:/code/last2/boros/world_model.json) defines what Boros must become. Currently it has **1 category**:

### `memory` — Cognitive Memory System

**Weight**: 3.0 · **Current Milestone**: 0 (Event Logging)

| Milestone | Level | Name | Difficulty | Unlock Score |
|---|---|---|---|---|
| 0 | Event Logging | 3 | 0.5 |
| 1 | Pattern Extraction | 6 | 0.6 |
| 2 | Associative Recall | 8 | 0.75 |
| 3 | Adaptive Memory Evolution | 10 | 0.9 |

**Milestone progression**: When a category's score consistently exceeds its `unlock_score`, `eval_check_milestone` advances `current_milestone` in `world_model.json`, increasing task difficulty and raising the bar.

Each milestone has:
- **Anchors**: Specific behaviors the agent must demonstrate
- **Rubric**: 4-level grading scale
- **Failure modes**: Known ways the agent can fail
- **Task template**: Behavioral instructions injected into eval tasks
- **Execution pattern**: Step-by-step expected workflow

---

## 8. The Memory Subsystem (6 Functions)

| Function | Purpose |
|---|---|
| `memory_page_in` | Load data from: scores, experiences, evolution_records, sessions, session_buffer |
| `memory_page_out` | Write key-value data to session buffer |
| `memory_search_sql` | Keyword search across all memory files |
| `memory_commit_archival` | Write structured entries (lesson/observation/fact) to `memory/experiences/` |
| `memory_kg_write` | Write temporal facts to knowledge graph (bitemporal JSONL) |
| `memory_kg_query` | Query knowledge graph with point-in-time support |

**Content validation**: `memory_commit_archival` requires entries of type `lesson` or `observation` to include `Context:`, `Action:`, and `Outcome:` phrases with minimum 100 characters. Empty templates are rejected.

**Knowledge graph**: Bitemporal design — each fact has `valid_from` and can be superseded. Supports `include_history=true` for full timeline and `as_of=<timestamp>` for point-in-time queries.

---

## 9. The Skill-Forge (9 Functions)

The forge is Boros's self-modification toolkit:

| Function | Purpose |
|---|---|
| `forge_snapshot` | Create restorable snapshot of a skill or file |
| `forge_validate` | Syntax-check Python files (`compile()` check) |
| `forge_test_suite` | Run `pytest` on a skill's test directory |
| `forge_apply_diff` | Apply find-and-replace patches to files |
| `forge_rollback` | Restore from a snapshot |
| `forge_invoke` | Test-execute a specific function |
| `forge_create_skill` | Scaffold new skill directory with full structure |
| `forge_read_skill_md` | Read a skill's SKILL.md with parsed sections |
| `forge_edit_skill_md` | Edit a specific section of a SKILL.md |

---

## 10. Safety Mechanisms

### 10.1 Path Guard

[path_guard.py](file:///e:/code/last2/boros/skills/tool-use/functions/_internal/path_guard.py) is described as **"the single most important safety mechanism in the system"**.

**Protected files** (cannot be modified by evolution):
`kernel.py`, `agent_loop.py`, `config.json`, `manifest.json`, `start.py`, `requirements.txt`, `tool_schemas.py`, `.env`, `.env.template`, `.git`, `.gitignore`

**Protected directories**: `eval-generator/`, `adapters/`, `.git/`, `commands/`

**Rule**: Only files under `skills/` can be modified by the evolution loop.

**Dangerous command patterns**: `rm -rf`, `del /s`, `pip install`, `pip uninstall`, format commands, and any redirect to infrastructure files are blocked.

### 10.2 Anti-Brute-Force

The [evolution_ledger.py](file:///e:/code/last2/boros/skills/meta-evolution/functions/_internal/evolution_ledger.py) tracks every mutation. If a file has been modified 2+ times in the last 3 attempts without improvement, `evolve_propose` blocks further proposals on that file.

### 10.3 Automatic Rollback

`eval_check_regression` compares new scores against `high_water_marks.json`. If any category regresses, the snapshot daemon automatically restores the skills directory.

### 10.4 Duplicate Tool Call Detection

The agent loop tracks tool call signatures. Identical non-polling calls are blocked to prevent infinite loops.

### 10.5 Empty Turn Enforcement

If the LLM produces 3 consecutive turns with no tool calls, the cycle is force-terminated.

### 10.6 Fail-Closed Review Board

If the meta-eval LLM is unavailable, all proposals are REJECTED by default.

### 10.7 Safety Net Commit

If the LLM ends its turn without calling `loop_end_cycle`, the agent loop calls it automatically (`_ensure_cycle_committed`).

---

## 11. LLM Provider Abstraction

All adapters normalize to a **canonical message format** (Anthropic-style blocks):

```json
{
  "content": [
    {"type": "text", "text": "..."},
    {"type": "tool_use", "id": "call_xxx", "name": "tool_name", "input": {...}}
  ],
  "stop_reason": "end_turn" | "tool_use" | "max_tokens",
  "usage": {"input_tokens": N, "output_tokens": M}
}
```

| Provider | File | Tool Support | SDK | Notes |
|---|---|---|---|---|
| **Gemini** | [gemini.py](file:///e:/code/last2/boros/adapters/providers/gemini.py) | ✅ | Raw REST API | Rate limit retry (429), 120s timeout, 3 attempts |
| **OpenAI** | [openai.py](file:///e:/code/last2/boros/adapters/providers/openai.py) | ✅ | Official SDK | Full format conversion (Anthropic ↔ OpenAI) |
| **Anthropic** | [anthropic.py](file:///e:/code/last2/boros/adapters/providers/anthropic.py) | ✅ | Official SDK | Native format, no conversion needed |
| **Ollama** | [ollama.py](file:///e:/code/last2/boros/adapters/providers/ollama.py) | ❌ | Raw HTTP | Text-only, no function calling |
| **OpenAI Compat** | [openai_compat.py](file:///e:/code/last2/boros/adapters/providers/openai_compat.py) | ❌ | OpenAI SDK | For Together, Groq, etc. Text-only |

**Two LLM roles**:
1. **`evolution_api`**: The primary agent brain (executes cycles, writes code)
2. **`meta_eval_api`**: The independent reviewer (evaluates diffs, grades tasks)

---

## 12. Fork / Re-Evolve / Adapt Lifecycle

This is the **deployment lifecycle** — how Boros transitions between self-improvement and production use.

```mermaid
stateDiagram-v2
    [*] --> Evolution: python start.py → evolve
    Evolution --> BrosFork: fork command
    BrosFork --> Evolution: re-evolve command
    BrosFork --> BrosFork: adapt / adapt-config
    
    state Evolution {
        [*] --> REFLECT
        REFLECT --> EVOLVE
        EVOLVE --> VALIDATE
        VALIDATE --> COMMIT
        COMMIT --> REFLECT
    }
    
    state BrosFork {
        [*] --> EmployeeMode
        EmployeeMode --> AdaptCycle: Scheduled or manual
        AdaptCycle --> EmployeeMode
    }
```

### Fork

1. Pauses evolution
2. Records epoch in `lineage.json` with high-water marks
3. Sets `agent_state: "boros-fork"` in loop state
4. Switches mode to `employee` (executes tasks from `commands/pending.json`)
5. Starts adaptation scheduler (background thread)

### Adaptation (while forked)

The [AdaptEngine](file:///e:/code/last2/boros/adapt_engine.py) runs on a configurable schedule (default: every 2 days):
1. Reads `logs/task_log.jsonl` for real task execution data
2. Compiles statistics (failure rate, retry rate)
3. Sends task data + current SKILL.md definitions to the evolution LLM
4. LLM proposes behavioral changes (SKILL.md edits, world model weight adjustments, minor code fixes)
5. Review board approves/rejects the batch
6. Approved changes are applied and hot-reloaded

**Key difference from evolution**: Adaptation evolves against **real usage patterns** (environmental pressure), not synthetic eval rubrics (self-improvement pressure). No rollback needed — changes are smaller in scope.

### Re-Evolve

1. Compiles recent deployment task log into `session/adapt_seed.json`
2. Records re-evolve event in `lineage.json`
3. Switches back to `mode: evolution`
4. Resumes the continuous evolution loop
5. The adapt_seed is injected into the first REFLECT, so Boros targets gaps discovered during real-world use

---

## 13. The Agent Loop (Execution Engine)

[agent_loop.py](file:///e:/code/last2/boros/agent_loop.py) is the LLM ↔ Tool dispatch engine. Two modes:

### Evolution Cycle (`run_evolution_cycle`)

1. Syncs world model state
2. Builds system prompt: BOROS.md + loop state + world model + scores + history + regression warnings + blocked files + hypothesis + high-water marks + bootstrap mode + environment info
3. Builds tool list from `TOOL_SCHEMAS` filtered to registered functions
4. Sends `cycle_prompt.md` as the user message
5. Loops: LLM response → parse tool calls → dispatch → return results → repeat
6. Limits: max 100 tool calls, 10-minute timeout, 500K token budget
7. Safety: duplicate detection, empty turn enforcement, auto-commit on termination

### Execution Cycle (`run_execution_cycle`)

Same dispatch loop but simpler:
- Uses `_execution_prompt` (no evolution instructions)
- Processes tasks from `commands/pending.json`
- No deduplication or proposal tracking
- Logs to `task_log.jsonl` for the adaptation engine

### Error Recovery

- Exponential backoff with jitter on failure: `min(300, 30 × 2^(fail_count - 1))` seconds
- Failed cycles are logged and the loop continues automatically

---

## 14. System Prompt Architecture

The system prompt is dynamically assembled from 11 layers:

| Layer | Source | Purpose |
|---|---|---|
| 1 | `BOROS.md` | Core identity, operating principles, constraints |
| 2 | `session/loop_state.json` | Current cycle, stage, mode |
| 3 | `world_model.json` | Active milestone anchors, rubrics, capability targets |
| 4 | `evals/scores/*.json` | Last 3 evaluation results |
| 5 | `memory/score_history.jsonl` | Last 5 score history entries |
| 6 | `memory/evolution_records/hyp-cycle*.json` | Past 10 hypothesis outcomes |
| 7 | Evolution ledger | Regression warnings + blocked files (injected inline) |
| 8 | `session/hypothesis.json` | Active task binding |
| 9 | `session/adapt_seed.json` | Field deployment history (after re-evolve) |
| 10 | `skills/eval-bridge/state/high_water_marks.json` | Current best scores |
| 11 | Bootstrap mode | If no scores exist, forces immediate eval before any evolution |

Plus environment detection (Windows vs Linux command guidance).

---

## 15. Skill Architecture (Uniform Structure)

Every skill follows a standardized directory layout:

```
skills/<skill-name>/
├── SKILL.md              # Semantic rules, behavioral instructions (modifiable by Boros)
├── skill.json            # Metadata and dependencies
├── changelog.md          # Change history
├── functions/            # Python implementation
│   ├── __init__.py       # Exports all public functions
│   ├── function_name.py  # Each function = one tool
│   └── _internal/        # Private helpers (not exported)
├── metrics/              # Performance tracking (optional)
└── tests/                # pytest test files
    └── test_basic.py     # Basic smoke tests
```

**Function signature**: Every tool function has the same signature:
```python
def tool_name(params: dict, kernel=None) -> dict:
```

**Loading**: The kernel imports `boros.skills.<skill-name>.functions` and registers each function listed in `manifest.json`'s `provided_functions` array.

**Hot-reloading**: `kernel.reload_skill(name)` reloads the module and re-registers all functions without restarting.

---

## 16. Infrastructure vs. Evolvable Skills

| Category | Skills | Can Boros Modify? |
|---|---|---|
| **Infrastructure (boot)** | mode-controller, memory, skill-router, context-orchestration, reflection, meta-evolution, meta-evaluation, loop-orchestrator | ❌ Banned by BOROS.md |
| **Evolvable (demand)** | skill-forge, reasoning, tool-use, web-research, eval-bridge, eval_util | ✅ These are the evolution targets |
| **Never modify (system)** | kernel.py, agent_loop.py, config.json, manifest.json, start.py, tool_schemas.py | ❌ Protected by path guard |

Note: Infrastructure skills are editable *by design* (their SKILL.md and functions are regular files), but the agent is **instructed** not to touch them. The path guard provides the hard enforcement only for system files — infrastructure skills rely on soft guardrails (prompt instructions + review board rejection).

---

## 17. Data Flow Summary

```mermaid
graph TB
    subgraph "Agent Loop"
        AL["AgentLoop"] -->|dispatch| KR["Kernel Registry"]
        KR -->|call| SKILLS["Skill Functions"]
    end
    
    subgraph "Evaluation"
        EB["eval-bridge"] -->|write request| REQ["shared/requests/"]
        REQ --> EG["EvalGenerator"]
        EG -->|write result| RES["shared/results/"]
        RES --> EB
    end
    
    subgraph "Persistence"
        SKILLS --> SS["session/"]
        SKILLS --> MEM["memory/"]
        SKILLS --> SNAP["snapshots/"]
        SKILLS --> HW["eval-bridge/state/"]
        SKILLS --> WM["world_model.json"]
    end
    
    subgraph "Ledger"
        LE["loop_end_cycle"] --> LEG["memory/evolution_ledger.jsonl"]
        LE --> KG["memory/knowledge_graph.jsonl"]
        LE --> SH["memory/score_history.jsonl"]
    end
```

---

## 18. Configuration Deep Dive

### [config.json](file:///e:/code/last2/boros/config.json)

| Key | Value | Purpose |
|---|---|---|
| `max_cycle_duration_minutes` | 10 | Hard time limit per evolution cycle |
| `max_tool_calls_per_cycle` | 100 | Maximum tool dispatches before forced termination |
| `auto_pause_on_regression` | true | Pause loop when scores drop |
| `snapshot_retention.keep_last` | 10 | Number of snapshots to retain |
| `eval_concurrency` | 2 | Parallel category evaluation threads |
| `eval_category_timeout_seconds` | 300 | Per-category timeout |
| `eval_max_agent_iterations` | 15 | Max LLM turns per eval task |
| `eval_tasks_per_category` | 3 | Tasks per category for score averaging |
| `eval_request_expiry_minutes` | 15 | Stale request cleanup threshold |

### [manifest.json](file:///e:/code/last2/boros/manifest.json)

| Key | Purpose |
|---|---|
| `boot_sequence` | Ordered skill loading (dependencies respected) |
| `skills` | Full registry: path, type (boot/demand), dependencies, provided_functions |
| `evolution.single_proposal_cycles` | First 20 cycles limited to 1 proposal each |
| `evolution.max_proposals_per_cycle` | After 20 cycles, up to 5 proposals |
| `evolution.modification_band` | Code changes limited to 5–50 lines |
| `context.max_context_tokens` | 200K token context window |
| `context.memory_token_cap` | 8K tokens for memory injection |
| `tool_routing` | `"unconstrained"` — all tools available at all times |

---

## 19. Strategic Objectives and Design Philosophy

### 19.1 Why Self-Evolution?

Boros is designed around the premise that **the best way to improve an AI agent is to let it improve itself**. Rather than manually tuning prompts and code, Boros:
- Identifies its own weaknesses through evaluation
- Hypothesizes improvements
- Implements code changes
- Tests them against adversarial scenarios
- Keeps what works, discards what doesn't

### 19.2 Why Two LLMs?

The dual-LLM architecture (evolution brain + review board) prevents the agent from:
- Approving its own bad code
- Gaming its evaluation criteria
- Making cosmetic changes that don't improve real capability

### 19.3 Why Milestones?

The progressive difficulty system prevents the agent from getting stuck at a local optimum. As it masters one level, the tasks get harder, forcing deeper capability development.

### 19.4 Why Fork/Re-Evolve?

This solves the **deploy-evolve tension**: you can't run a production agent while it's rewriting its own code. The fork mechanism freezes a known-good state for deployment, while re-evolve incorporates real-world feedback into the next evolution cycle.

### 19.5 Why an Evolution Ledger?

Every mutation is permanently recorded with its score impact. This creates **institutional memory** — Boros can query "what has been tried before on this file?" and avoid repeating failed approaches.

---

## 20. Current State of the Clone

Based on `lineage.json`, this repository has been through:
- **1 fork event** (Generation 0, forked at cycle 2)
- High-water mark at fork: `memory: 0.459`
- Currently in `boros-fork` state with `adaptation_interval: "2d"`

The world model currently defines only the **memory** category with 4 progressive milestones. To expand Boros's capabilities, you would add more categories to `world_model.json` (e.g., web_search, reasoning, tool_use).

---

## 21. File Count Summary

| Component | Files | Lines of Code |
|---|---|---|
| Core engine (start, kernel, agent_loop, adapt_engine, tool_schemas) | 5 | ~1,530 |
| LLM Adapters | 6 | ~450 |
| Eval Generator | 3 | ~800 |
| Skills (15 dirs, 87 Python files) | 93 | ~6,500+ |
| Configuration / Data (JSON, MD) | 8 | ~700 |
| **Total** | **~115 files** | **~10,000+ lines** |
