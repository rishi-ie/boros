"""model_switch_get — returns current active model configuration."""

import json
import os
from pathlib import Path


def model_switch_get(params: dict, kernel=None) -> dict:
    """
    Get the current active model configuration.
    
    Returns:
        - evolution_api: current evolution provider/model
        - meta_eval_api: current meta evaluation provider/model  
        - session_override: any runtime overrides from session
    """
    boros_dir = str(kernel.boros_root) if kernel else os.getcwd()
    config_path = Path(boros_dir) / "config.json"
    session_override_path = Path(boros_dir) / "session" / "active_model.json"
    
    result = {}
    
    # Read base config
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
            providers = config.get("providers", {})
            result["evolution_api"] = providers.get("evolution_api", {})
            result["meta_eval_api"] = providers.get("meta_eval_api", {})
        except Exception as e:
            return {"status": "error", "message": f"Failed to read config: {e}"}
    
    # Check for runtime overrides
    if session_override_path.exists():
        try:
            with open(session_override_path) as f:
                override = json.load(f)
            result["session_override"] = override
        except Exception:
            pass
    
    result["status"] = "ok"
    return result