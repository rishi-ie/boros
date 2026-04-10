import os
import py_compile
from ._internal.path_guard import is_path_protected

def tool_file_edit_diff(params: dict, kernel=None) -> dict:
    target_file = params.get("target_file")
    replacement_chunks = params.get("replacement_chunks", [])
    
    if not target_file: return {"status": "error", "message": "target_file required"}

    # Resolve relative paths to boros root (matches tool_file_write behavior)
    if kernel and not os.path.isabs(target_file):
        target_file = os.path.join(str(kernel.boros_root), target_file)

    if not os.path.exists(target_file): return {"status": "error", "message": f"file not found: {target_file}"}
    
    # FIX-01: Enforce path protection
    if kernel:
        protected, reason = is_path_protected(target_file, str(kernel.boros_root))
        if protected:
            return {"status": "error", "message": f"BLOCKED: {reason}"}

    try:
        with open(target_file, "r") as f:
            original_content = f.read()
            
        content = original_content
        for chunk in replacement_chunks:
            target = chunk.get("target_content", "")
            replacement = chunk.get("replacement_content", "")
            if target not in content:
                return {"status": "error", "message": f"Target content not found in file: {target[:50]}..."}
            content = content.replace(target, replacement, 1)

        with open(target_file, "w") as f:
            f.write(content)
            
        # Verify syntax safety if python file
        if target_file.endswith(".py"):
            try:
                py_compile.compile(target_file, doraise=True)
            except py_compile.PyCompileError as build_err:
                # Critical safety net: Auto-revert file if syntax is broken
                with open(target_file, "w") as f:
                    f.write(original_content)
                return {
                    "status": "error", 
                    "message": f"Patch created invalid Python syntax. AUTO-REVERTED.\nSyntaxError Details:\n{str(build_err)}"
                }
            
        return {"status": "ok", "message": "Patch applied successfully and passed syntax verification."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
