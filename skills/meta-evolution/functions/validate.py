import os

def validate_skill_syntax(skill_name: str, kernel=None) -> dict:
    """
    Validates the syntax of all Python files within a given skill.
    This is a pre-flight check before proposing a change.
    """
    if not kernel:
        return {"status": "error", "message": "Kernel not available for validation."}
    
    # This is the correct way to invoke another tool from within a function.
    validation_result = kernel.registry['forge_validate']({"target": skill_name}, kernel)
    
    return validation_result
