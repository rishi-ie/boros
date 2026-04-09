"""Path Guard — Prevents Boros from modifying its own infrastructure files.

This is the single most important safety mechanism in the system.
Without it, one bad LLM decision can permanently brick Boros.
"""

import os

# Files that must NEVER be modified by the evolution loop
PROTECTED_PATHS = {
    "kernel.py",
    "agent_loop.py",
    "config.json",
    "manifest.json",
    "start.py",
    "requirements.txt",
    "tool_schemas.py",
    ".env",
    ".env.template",
    ".git",
    ".gitignore",
}

# Directories that must never be modified
PROTECTED_DIRS = {
    "eval-generator",
    "adapters",
    ".git",
    "commands",
}

def is_path_protected(file_path: str, boros_root: str) -> tuple:
    """Returns (is_protected, reason) for a given file path.
    
    Args:
        file_path: The path being written/edited/deleted.
        boros_root: The root directory of the Boros installation.
    
    Returns:
        (True, reason) if the path is protected and must not be modified.
        (False, "") if the path is safe to modify.
    """
    try:
        rel = os.path.relpath(os.path.abspath(file_path), os.path.abspath(boros_root))
    except ValueError:
        # Different drives on Windows — path is outside boros, allow it
        return False, ""
    
    rel_normalized = rel.replace("\\", "/")

    # Reject anything that tries to escape the boros directory
    if rel_normalized.startswith(".."):
        return True, f"Path escapes the boros directory: {rel_normalized}"

    # Check exact file matches
    for protected in PROTECTED_PATHS:
        if rel_normalized == protected or rel_normalized.endswith("/" + protected):
            return True, f"'{protected}' is a protected infrastructure file"

    # Check directory matches
    for protected_dir in PROTECTED_DIRS:
        if rel_normalized.startswith(protected_dir + "/") or rel_normalized == protected_dir:
            return True, f"'{protected_dir}/' is a protected infrastructure directory"

    # Only allow modifications inside skills/ directory
    if not rel_normalized.startswith("skills/"):
        return True, f"Only files under skills/ can be modified by the evolution loop. Got: {rel_normalized}"

    return False, ""


# Dangerous shell command patterns
DANGEROUS_PATTERNS = [
    "rm -rf", "del /s", "rmdir /s", "> kernel.py", "> agent_loop.py",
    "> config.json", "> manifest.json", "format ", "mkfs",
    "> start.py", "> tool_schemas.py", "> .env",
    "pip uninstall", "pip install",  # prevent dependency tampering
]

def is_command_dangerous(command: str) -> tuple:
    """Check if a shell command could damage Boros infrastructure.
    
    Returns:
        (True, reason) if the command is dangerous.
        (False, "") if the command appears safe.
    """
    cmd_lower = command.lower().strip()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in cmd_lower:
            return True, f"Command contains dangerous pattern: '{pattern}'"
    return False, ""
