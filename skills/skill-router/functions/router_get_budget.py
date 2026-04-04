
def router_get_budget(params: dict, kernel=None) -> dict:
    if kernel:
        max_calls = kernel.config.get("max_tool_calls_per_cycle", 100)
        return {"status": "ok", "max_tool_calls": max_calls, "max_context_tokens": kernel.manifest.get("context", {}).get("max_context_tokens", 200000)}
    return {"status": "ok", "max_tool_calls": 100}
