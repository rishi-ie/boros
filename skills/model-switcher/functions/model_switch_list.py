"""model_switch_list — list available models from config."""

import json
import os
from pathlib import Path


def model_switch_list(params: dict, kernel=None) -> dict:
    """
    List all available models/providers.
    
    Returns:
        - available_models: list of configured models
        - recommended: suggested model for evolution
    """
    boros_dir = str(kernel.boros_root) if kernel else os.getcwd()
    config_path = Path(boros_dir) / "config.json"
    
    models = []
    
    # Read from config.json if exists
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
            
            # Get available_models list
            if "available_models" in config:
                models = config["available_models"]
            
            # Also parse providers
            providers = config.get("providers", {})
            for target, cfg in providers.items():
                provider = cfg.get("provider", "")
                model = cfg.get("model", "")
                
                # Avoid duplicates
                if not any(m.get("name") == model and m.get("provider") == provider for m in models):
                    models.append({
                        "name": model,
                        "provider": provider,
                        "target": target
                    })
        except Exception as e:
            return {"status": "error", "message": f"Failed to read config: {e}"}
    
    # Recommended model for evolution
    recommended = {
        "evolution": {"provider": "minimax", "model": "MiniMax-Text-01"},
        "meta_eval": {"provider": "gemini", "model": "gemini-2.5-flash"},
        "eval_generator": {"provider": "openai", "model": "gpt-4o"}
    }
    
    return {
        "status": "ok",
        "available_models": models,
        "recommended": recommended
    }