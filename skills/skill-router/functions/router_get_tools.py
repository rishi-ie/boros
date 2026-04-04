
def router_get_tools(params: dict, kernel=None) -> dict:
    """Return all available tool names and descriptions, including their arguments."""
    if kernel:
        tool_details = []
        for tool_name, tool_func in kernel.registry.items():
            tool_description = tool_func.__doc__.strip() if tool_func.__doc__ else "No description available."
            # Extract arguments from the function signature
            import inspect
            sig = inspect.signature(tool_func)
            args = []
            for name, param in sig.parameters.items():
                if name != 'kernel' and name != 'params':  # Exclude internal parameters
                    arg_type = param.annotation
                    if hasattr(arg_type, '__name__'):
                        arg_type_str = arg_type.__name__
                    else:
                        arg_type_str = str(arg_type)
                    args.append({"name": name, "type": arg_type_str, "default": str(param.default) if param.default != inspect.Parameter.empty else "No default"})
            tool_details.append({"name": tool_name, "description": tool_description, "arguments": args})
        return {"status": "ok", "tools": tool_details, "count": len(tool_details)}
    return {"status": "ok", "tools": [], "count": 0}
