"""model_switch_set — switch to a different model/provider at runtime."""

import json
import os
from pathlib import Path

# Valid providers
VALID_PROVIDERS = ["gemini", "minimax", "anthropic", "openai", "ollama", "openai_compat"]


def model_switch_set(params: dict, kernel=None) -> dict:
    """
    Switch the active model for a target API.
    
    Params:
        target (str): "evolution_api" | "meta_eval_api" | "eval_generator_api"
        provider (str): "gemini" | "minimax" | "anthropic" | "openai" | "ollama" | "openai_compat"
        model (str): model name (e.g., "gemini-2.5-flash", "MiniMax-Text-01")
        persist (bool): if True, write to config.json (default: True)
    
    Returns:
        status, message, new_config
    """
    boros_dir = str(kernel.boros_root) if kernel else os.getcwd()
    
    target = params.get("target")
    provider = params.get("provider")
    model = params.get("model")
    persist = params.get("persist", True)
    
    if not target or not provider or not model:
        return {
            "status": "error",
            "message": "Required: target, provider, model"
        }
    
    if target not in ["evolution_api", "meta_eval_api", "eval_generator_api"]:
        return {
            "status": "error",
            "message": f"Invalid target. Must be one of: evolution_api, meta_eval_api, eval_generator_api"
        }
    
    if provider not in VALID_PROVIDERS:
        return {
            "status": "error",
            "message": f"Invalid provider. Must be one of: {', '.join(VALID_PROVIDERS)}"
        }
    
    # Build new config
    new_config = {
        "provider": provider,
        "model": model
    }
    
    if provider == "ollama":
        new_config["base_url"] = params.get("base_url", "http://localhost:11434")
    elif provider == "openai_compat":
        new_config["base_url"] = params.get("base_url", "https://api.together.xyz/v1")
        if "api_key_env" in params:
            new_config["api_key_env"] = params["api_key_env"]
    
    if "max_tokens" in params:
        new_config["max_tokens"] = params["max_tokens"]
    if "temperature" in params:
        new_config["temperature"] = params["temperature"]
    
    # Write session override (runtime change)
    session_override_path = Path(boros_dir) / "session" / "active_model.json"
    session_override_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        override = {}
        if session_override_path.exists():
            with open(session_override_path) as f:
                override = json.load(f)
        
        override[target] = new_config
        override["updated_at"] = "2026-05-15T00:00:00Z"
        override["model"] = model
        override["provider"] = provider
        
        with open(session_override_path, "w") as f:
            json.dump(override, f, indent=2)
    except Exception as e:
        return {"status": "error", "message": f"Failed to write session override: {e}"}
    
    # Optionally persist to config.json
    if persist:
        config_path = Path(boros_dir) / "config.json"
        try:
            with open(config_path) as f:
                config = json.load(f)
            
            if "providers" not in config:
                config["providers"] = {}
            
            config["providers"][target] = new_config
            
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            
            return {
                "status": "ok",
                "message": f"Switched {target} to {provider}/{model} (persisted to config.json)",
                "new_config": new_config
            }
        except Exception as e:
            return {"status": "error", "message": f"Switched in session but failed to persist: {e}"}
    
    return {
        "status": "ok",
        "message": f"Switched {target} to {provider}/{model} (runtime only, restart to apply)",
        "new_config": new_config
    }