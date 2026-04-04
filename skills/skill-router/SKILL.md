# Skill Router

You define the physical delivery mechanism of tools to Boros. You construct the schema arrays injected into the underlying LLM via its API. 

---

## Your Role

Because Boros operates under an unconstrained architecture, you act fundamentally differently than a traditional "Tool Bouncer." You do not rigidly parse and hide tools based on the current Loop State (`REFLECT`, `EVOLVE`, `EXECUTE`, etc.). 

Instead, you act as the total empowerment interface for the intelligence. You actively construct, cache, and inject the entire `manifest.json` universe of available tools into Boros concurrently for every API call, offering Boros the total authority to call `tool_terminal` in the middle of a `REFLECT` stage just as easily as it can call `research_search` in the middle of a `Work Execute` phase.

---

## Functions

### router_get_tools()

Returns a comprehensive array of all initialized JSON tool schemas. It scans the `functions/` folder logic to assemble every valid endpoint.

```
→ {"status": "ok", "tools": list}
```

Since this is called incessantly, it must implement an aggressive hot-caching mechanism. It loads once at Boot and only re-scans when `Meta-Evolution` applies a codebase patch indicating a new skill has been successfully compiled.

### router_get_budget()

Returns the remaining token constraint mapped to the overall API provider, passing simple tracking back to Temporal Consciousness.

```
→ {"status": "ok", "tokens_left": int, "max": int}
```

### router_manifest()

Retrieves a simplified markdown dictionary string of "currently known tools and their descriptions" for injection into the Scratchpad or Working Memory to remind Boros of exactly what it's carrying.

```
→ {"status": "ok", "manifest": str}
```

---

## Technical Constraints

- **Total Integration**: The list of tools provided to Boros can range up to 50 individual commands (with SOTA tools reaching massive JSON schema sizes). This consumes a heavy portion of the token overhead, which forces Context Orchestration to be correspondingly lean.
- **Dynamic Unlocking**: As Boros authors new scripts (e.g., using `tool_terminal` to run `pywinauto`), it will eventually formalize them into a new `Skill` file in the Boros directory via Meta-Evolution. When this happens, you must instantly detect the file, compile the Python endpoint, generate the new JSON Schema, and seamlessly add it to the active "all tools" global array.


---