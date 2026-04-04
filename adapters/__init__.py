import importlib

def load_adapter(role_config: dict):
    provider = role_config.get("provider")
    if not provider:
        raise ValueError("No provider specified in role config")
    
    try:
        module = importlib.import_module(f"boros.adapters.providers.{provider}")
        
        # Capitalize and handle snake_case to CamelCase (e.g., openai_compat -> Openai_compatAdapter -> OpenaiCompatAdapter)
        class_name = "".join(x.capitalize() for x in provider.split("_")) + "Adapter"
        adapter_class = getattr(module, class_name)
        return adapter_class(role_config)
    except Exception as e:
        raise RuntimeError(f"Failed to load adapter for provider {provider}: {e}")
