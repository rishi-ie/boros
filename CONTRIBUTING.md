# Contributing to Boros

## Ways to Contribute

- **Add a new world model category** — define a new capability for Boros to evolve toward
- **Add a new skill** — extend Boros's capabilities with a new modular skill
- **Add a new LLM adapter** — enable Boros to run on more providers
- **Fix bugs** — see `suggestions.md` for the known issue list
- **Improve existing skills** — better implementations of any skill function

---

## Adding a New World Model Category

Edit `world_model.json` to add a new entry under `categories`. Every category needs:

```json
"your_category_id": {
  "name": "Human Readable Name",
  "description": "What this capability means and how it's measured",
  "final_state": "What Level 4 mastery looks like in practice",
  "anchors": [
    "Specific observable behavior 1",
    "Specific observable behavior 2"
  ],
  "rubric": {
    "level_1": "Description of baseline/failure",
    "level_2": "Partial capability",
    "level_3": "Functional capability",
    "level_4": "Full mastery — what you want Boros to achieve"
  },
  "failure_modes": ["Common ways agents fail at this"],
  "related_skills": ["existing-skill-name"],
  "weight": 1.5
}
```

**`related_skills` must match actual directory names** in `skills/`. Run `ls skills/` to see valid names.

---

## Adding a New Skill

```bash
# Use the Skill Forge (from within the Director terminal):
boros task "Create a new skill called 'my-skill' that does X"

# Or scaffold manually:
mkdir -p skills/my-skill/functions
mkdir -p skills/my-skill/state
mkdir -p skills/my-skill/tests
```

Every skill needs:
- `SKILL.md` — describes the skill's role, rules, and behavioral guidelines
- `skill.json` — metadata (`version`, `description`, `type`)
- `functions/__init__.py` — exports all functions
- `functions/your_function.py` — each function takes `(params: dict, kernel=None) -> dict`
- `tests/test_basic.py` — at minimum a health check

Register the skill in `manifest.json` under `"skills"` and add its function schemas to `tool_schemas.py`.

---

## Adding a New LLM Adapter

Create `adapters/providers/your_provider.py`:

```python
from boros.adapters.base_adapter import BaseAdapter

class YourproviderAdapter(BaseAdapter):
    def __init__(self, config):
        self.model = config.get("model", "default-model")
        # ...

    def complete(self, messages: list, tools: list = None, system: str = None) -> dict:
        # Must return:
        # {
        #   "content": [{"type": "text", "text": "..."} | {"type": "tool_use", "id": "...", "name": "...", "input": {...}}],
        #   "stop_reason": "end_turn" | "tool_use" | "max_tokens",
        #   "usage": {"input_tokens": N, "output_tokens": N}
        # }
        ...
```

The class name must be `YourproviderAdapter` (capitalize each `_`-separated word + `Adapter`).

Then configure it in `config.json`:
```json
"evolution_api": {
  "provider": "your_provider",
  "model": "model-name"
}
```

---

## Skill Function Contract

Every skill function must follow this signature:

```python
def function_name(params: dict, kernel=None) -> dict:
    """Docstring."""
    # Always return a dict with at minimum {"status": "ok"} or {"status": "error", "message": "..."}
    ...
```

- `params` — the LLM's tool call input (dict)
- `kernel` — the `BorosKernel` instance (gives access to `kernel.boros_root`, `kernel.registry`, `kernel.evolution_llm`, `kernel.meta_eval_llm`)
- Return dict must always have a `"status"` key

---

## Running Tests

```bash
# Run all skill tests
pytest skills/

# Run a specific skill's tests
pytest skills/reasoning/tests/

# Run the full system (requires API keys in .env)
python run.py
```

---

## Code Style

- No external dependencies beyond `requirements.txt` inside skill functions
- Use `os.path.join` and `pathlib.Path` — never hardcoded string paths
- Never use bare `except:` — always catch specific exceptions
- Skill functions must be stateless — all state lives in files under `session/`, `memory/`, or `skills/*/state/`
