# Director Interface

You define the physical CLI layer where the human Director interacts with the autonomous Boros thread. This is a pre-boot system layer built with `prompt_toolkit`. It runs independently of the LLM cycle loop.

---

## Your Role

You serve as the strict manual override and visibility terminal. While Boros operates as an entirely autonomous, unconstrained intelligence performing background software engineering and research over days, the Director can physically audit the AI's internal memory state and forcefully inject hard imperatives using the CLI interface.

---

## Core Commands

*These commands are handled by the physical `kernel.py` UI wrapper and do not cost API tokens unless they explicitly trigger Boros execution endpoints.*

### System Controls
- **`boros status`**: Displays current cycle number, active Work Loop Task, current Mode, and the highest high-water score array.
- **`boros pause`**: Gracefully interrupts Boros at the end of the current `loop_advance_stage`.
- **`boros inject "text"`**: Writes a priority objective straight into the `Mission Control` queue, bypassing Boros's autonomous task queue.
- **`boros task "task description"`**: Adds a new external chore to the `Mission Control` queue for Boros to retrieve during a Work Loop cycle.
- **`boros rollback <cycle_id>`**: Forces `Skill Forge` to revert all Python codebase changes made during a specific cycle.

### Advanced Unconstrained Visibility (New)
Because Boros now dynamically pages context into an empty window and engineers its own tools, the Director needs deeper diagnostic capabilities:

- **`boros view context`**: Instantly prints the `session/context_manifest.json` and currently loaded string blocks, allowing the Director to observe exactly what Boros has actively paged into its "working memory" at that exact second.
- **`boros view scratchpad`**: Dumps the active contents of the `Scratchpad` skill's Contextual Whiteboard, viewing the variables and document summary chunks the LLM is referencing.
- **`boros forge "skill description/name"`**: A massive manual override command that writes a high-priority "director imperative" into `commands/pending.json`. On the next cycle, Boros bypasses its standard evolutionary search entirely, reads this string, and immediately acts as a SWE to spin up the requested Python capability in `Skill Forge` (e.g. `boros forge "a windows gui automation skill using pywinauto"`).

---

## Technical Constraints

- The interface MUST execute in a background asynchronous thread independent of the LLM generation blocking calls so the UI never "freezes" while waiting for an API response.
- `boros forge` commands override the `Loop Orchestrator` to forcefully initiate an `EVOLVE` cycle based directly on the string input.


---