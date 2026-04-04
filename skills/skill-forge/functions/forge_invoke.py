
def forge_invoke(params: dict, kernel=None) -> dict:
    """Invoke a specific registered function for testing."""
    function_name = params.get("function_name", "")
    invoke_params = params.get("params", {})
    if not function_name:
        return {"status": "error", "message": "function_name required"}
    if kernel and function_name in kernel.registry:
        try:
            result = kernel.registry[function_name](invoke_params, kernel)
            return {"status": "ok", "result": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    return {"status": "error", "message": f"Function {function_name} not found in registry"}
