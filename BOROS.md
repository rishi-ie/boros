# BOROS Substrate: Single Source of Truth

**Paradigm:** Unconstrained Autonomy. Boros is an autonomous, self-modifying software engineering substrate. It natively evolves its own architecture, authors its own execution pipelines, and measures its performance against a rigorous, independent external Outcome Validator (Eval Generator). 

This file acts as the ultimate reference doc and System Instruction Set for any LLM driving this substrate.

---

## 1. Directory Structure & Anatomy

The Boros environment is rigidly structured into isolated functional domain boundaries. If you are a freshly connected LLM attempting to interface or evolve the system, strictly adhere to these mappings:

**IMPORTANT**: All paths below are relative to the boros root directory (your CWD). Do NOT prefix with `boros/`.
On Windows: use `type` instead of `cat`, `dir` instead of `ls`, and backslashes in paths.
Example: `type skills\memory\functions\memory_page_in.py`

```text
./                               # CWD = boros root (e.g., D:\x-cube\boros on Windows)
├── .env.template                # Global API credential configurations
├── config.json                  # Engine timers, logging, and fallback adapter overrides
├── manifest.json                # Master skill definitions, boot orders, and payload signatures
├── kernel.py                    # The mechanical beating heart. Auto-loads adapters and tool functions
├── world_model.json             # THE EVOLUTION ANCHOR. Defines what Boros must become.
├── adapters/                    # Provider connections (Anthropic, OpenAI, etc.) via base_adapter 
├── commands/                    # Interactive Director UI queue -> `pending.json`
├── evals/                       # World Model scoring thresholds and categories
├── logs/                        # `cycles.log`, `errors.log`, etc.
├── memory/                      # **The Moat**. Contains Long-Term memory structures:
│   ├── evolution_records/       # Historical patches, diffs, and verdicts
│   ├── experiences/             # Qualitative lessons and narrative facts
│   ├── sessions/                # Short-term rolling buffer states
│   └── score_history.jsonl      # Chronological ledger of dual-scoring evaluations
├── session/                     # Volatile cycle state (`current_cycle.json`)
├── skills/                      # The Autonomous Brain lobes
│   └── [skill-name]/            # e.g., `tool-use`, `memory`, `meta-evolution`
│       ├── SKILL.md             # The semantic intent and prompt instruction of the capability
│       ├── skill.json           # Physical skill metadata
│       └── functions/           # The ACTUAL python algorithms (evolved by Boros)
└── eval-generator/              # An independent sandbox environment to test Boros's capabilities
```

---

## 2. The Unconstrained Dual-Mode Loop

Boros operates in two foundational modes governed by `mode-controller`. The `kernel.py` loads the components, and the `Loop Orchestrator` spins the timing.

### Mode: Execution 
Boros acts as a purely functional digital employee. It continuously checks the CLI director queue (`pending.json`) or acts upon immediate tasks, using its registered `tool-use` logic.

### Mode: Evolution
Boros compounds intelligence via a 3-stage infinite recursive loop. The world model (`world_model.json`) defines the target capabilities. The system automatically reads the world model at each cycle start, so adding/removing categories in the world model immediately redirects evolution.

1. **REFLECT**: Read evaluation scores, call `evolve_orient` to identify the weakest world model category, and write a hypothesis targeting the `related_skills` for that category.
2. **EVOLVE**: Take the hypothesis, read the target skill's function files using `tool_terminal`, write real Python improvements using `tool_file_edit_diff`, submit the diff to the Meta-Evaluation Review Board, and apply if approved.
3. **EVAL**: Call `eval_request` to generate a sandbox evaluation, then `eval_read_scores` to get fresh scores, and `eval_check_regression` to verify improvement.

---

## 3. Tool Utilization & Unconstrained Execution

You are granted unbounded file system capability. Do not artificially throttle operations.

Boros natively interfaces with the Substrate through **Skill #14 — Tool Use**, which supplies:
- `tool_terminal(command, background)`: For running native Powershell/Bash environments. Returns `stdout`. Captures asynchronous `job_id` keys for background daemon spins.
- `tool_file_edit_diff(target_file, replacement_chunks)`: Surgical multi-instance diff-block replacement, rendering monolithic file-rewriting obsolete.

All Python scripts are auto-resolved relative to the project container, meaning `import boros` naturally queries upwards without configuration limits.

---

## 4. Adapters & LLM Connectivity

The physical "Brain" of Boros communicates through `adapters/base_adapter.py`. 
Any API LLM (Claude, GPT, Ollama) hooks directly into the factory function located in `kernel.py`:
```python
self.evolution_llm = load_adapter(self.config["providers"]["evolution_api"])
self.meta_eval_llm = load_adapter(self.config["providers"]["meta_eval_api"])
```

**If you are a fresh Agent tasked with bringing Boros online:**
1. Populate actual payload serializations inside `adapters/providers/anthropic.py` (or `openai.py`) tracking `params` arrays and mapping to `.env` keys.
2. Intercept the placeholder logic in `boros/skills/director-interface/functions/interface.py` to strip the temporary `time.sleep(2)` scaffold and seamlessly query `evolution_llm` sequentially.

---

## 5. Core Skill Reference Matrix

There are 15 unique Capabilities separated natively into *Boot* sequences (load sequentially verifying constraints) and *Demand* load structures (dynamically invoked as necessary to offset token burn).

| Classification | Essential Skills | Description |
| :--- | :--- | :--- |
| **Director** | `director-interface` | The asynchronous `prompt_toolkit` Terminal UI wrapper. |
| **Boot Core** | `memory`, `skill-router`, `reflection`, `context-orchestration` | Establishes physical database connections, mapping tools, and cycle starting analysis blocks. |
| **Boot Evolution** | `meta-evolution`, `meta-evaluation`, `loop-orchestrator` | Proposes raw codebase changes, rigorously audits diff regressions, and manages the state definitions (`session/`). |
| **Demand** | `tool-use`, `skill-forge`, `web-research`, `eval-bridge` | Physical filesystem manipulation, automated PyTest safety compiling, headless browser integrations, and the bridge to the dual-scoring Eval Sandbox. |

---

## 6. How to Extend This Source of Truth

**Boros is designed to self-mutate.**
As you natively rewrite the Python functionality of `boros/skills/*/functions`, you must independently maintain alignment with this `BOROS.md` truth block. Evolve the system safely.
