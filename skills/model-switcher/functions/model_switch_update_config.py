"""model_switch_update_config — directly update config.json providers."""

import json
import os
from pathlib import Path


def model_switch_update_config(params: dict, kernel=None) -> dict:
    """
    Directly update the config.json providers section.
    
    Params:
        providers (dict): Full providers object to write
            e.g., {
                "evolution_api": {"provider": "minimax", "model": "MiniMax-Text-01"},
                "meta_eval_api": {"provider": "gemini", "model": "gemini-2.5-flash"}
            }
    
    Returns:
        status, message, updated_config
    """
    boros_dir = str(kernel.boros_root) if kernel else os.getcwd()
    config_path = Path(boros_dir) / "config.json"
    
    providers = params.get("providers")
    if not providers:
        return {"status": "error", "message": "Required: providers dict"}
    
    try:
        with open(config_path) as f:
            config = json.load(f)
        
        if "providers" not in config:
            config["providers"] = {}
        
        config["providers"].update(providers)
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        
        return {
            "status": "ok",
            "message": "Config updated",
            "updated_config": config["providers"]
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to update config: {e}"}