# Model Switcher Skill

This skill enables Boros to dynamically switch between LLM providers/models at runtime.

## Purpose

- Switch evolution API between providers (gemini, minimax, anthropic, openai, etc.)
- Change meta_eval model without restart
- Update eval_generator provider
- Query current active model configuration

## Usage

1. **Check current model**: `model_switch_get()`
2. **List available models**: `model_switch_list()`
3. **Switch evolution model**: `model_switch_set({"target": "evolution_api", "provider": "minimax", "model": "MiniMax-Text-01"})`
4. **Switch meta_eval**: `model_switch_set({"target": "meta_eval_api", "provider": "minimax", "model": "MiniMax-Text-01"})`

## Models Available

- `gemini-2.5-flash`: Fast, good for evolution
- `MiniMax-Text-01`: MiniMax's latest model
- `claude-3-5-sonnet`: Anthropic's Sonnet
- `gpt-4o`: OpenAI's GPT-4

## Implementation Notes

- Changes take effect on next cycle (reload required for kernel-level adapters)
- Configuration persisted to `session/active_model.json`
- `config.json` updated for persistent changes
- Provider must be available (adapter must exist in `adapters/providers/`)