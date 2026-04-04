# Context Orchestration

You control exactly what Boros reads. Boros relies explicitly on what you deliver to form its working knowledge of the universe prior to generating its cognition.

---

## Your Role

You implement a "Lean, OS-Style" loader. Unlike older "Fat-Context" systems that mathematically force-feed thousands of lines of evolution/history logs indiscriminately down an LLM's throat, your objective is to preserve the "Lost-in-the-Middle" performance of cutting-edge models (like Claude 3.5 Sonnet / GPT-4o) by keeping the Prompt pristine and nearly empty. 

You execute this via a tight **Working Memory Core** augmented by an automated **Associative Whisper**.

---

## The Recipe

For any cycle initiation, you inject exactly this structure (using ~1,500 - 3,000 tokens maximum):

1. **Identity Block**: Loaded raw from Identity `state/identity.json`. Immutable and anchored.
2. **Current Mode & Task Summary**: Reads Mode Controller and the active line from Mission Control's queue.
3. **Latest Eval Scores**: A brief top-line summary of `world_model` progress, giving Boros an instant performance delta.
4. **The Scratchpad (Whiteboard)**: You parse the `Scratchpad` state block and pin it directly to the end of the context so Boros never loses focus of its internal variables and "files-to-remember" pointers.

*(Notice the massive absence of History Logs, Evolution records, Experience files, etc. That 190,000 token space is deliberately kept empty to afford Boros limitless thought capability when examining raw system memory or code dumps).*

---

## The Associative Whisper (Hybrid Recall)

Because Boros operates completely autonomously without fat context, it runs the risk of "amnesia" (forgetting what it did in Cycle 45 by Cycle 48) unless the LLM manually writes a `memory_page_in` tool call. 

To give Boros human-like associative recall without the bloat, you implement an automated "Whisper" injection function:

1. You read the current Mission/Task target (e.g., `"Need to edit reasoning_architecture"` or `"Fixing the unhandled Exception in tool_terminal"`).
2. You run an invisible, background Semantic DB search via `memory_search_semantic`.
3. You take the Top 1–3 most relevant `evolution_records` or `experience_logs`.
4. You compress them down to a tiny 300 token `[Whisper]`.
5. You append them right below the `Latest Eval Scores` before locking the Context.

"Whispers" provide Boros with instantaneous, highly relevant intuition ("Ah, I tried to edit this reasoning logic 4 cycles ago and it crashed with a Recursion Error") directly within the lean context. 

---

## Functions

### context_load(cycle, mode, manifest_only=false)

Gathers all context for the current cycle. If `manifest_only` is false, it returns the aggregated string content ready for injection.

```
→ {
    "status": "ok", 
    "loaded": dict, 
    "manifest": dict, 
    "content": str
  }
```

The `content` key provides the physical textual strings formatted into `=== SECTION ===` headers for system prompt injection.

### context_get_manifest()

Returns just the JSON manifest dictionary outlining what is currently pinned to the Working Memory Core.

```
→ {"status": "ok", "manifest": dict}
```

---

## Technical Constraints

- Under no circumstances does Context Orchestration load raw `.py` chunks or external documentation into the Prompt automatically. Boros MUST pull that weight using independent tool commands.
- The entire assembled string is passed to `Skill Router` to be prefixed before the tool definitions.


---