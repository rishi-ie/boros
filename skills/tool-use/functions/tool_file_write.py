import os
import py_compile
from ._internal.path_guard import is_path_protected

def tool_file_write(params: dict, kernel=None) -> dict:
    """Write content to a file, creating it if it doesn't exist.
    Use this to create new Python skill functions or any file from scratch.
    After writing, Python files are syntax-checked automatically."""
    path = params.get("path", "")
    content = params.get("content", "")

    if not path:
        return {"status": "error", "message": "path required"}

    # Resolve relative to boros root
    if kernel and not os.path.isabs(path):
        full_path = os.path.join(str(kernel.boros_root), path)
    else:
        full_path = path

    # FIX-01: Enforce path protection
    if kernel:
        protected, reason = is_path_protected(full_path, str(kernel.boros_root))
        if protected:
            return {"status": "error", "message": f"BLOCKED: {reason}"}


    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Syntax check Python files before confirming success
        if full_path.endswith(".py"):
            try:
                py_compile.compile(full_path, doraise=True)
            except py_compile.PyCompileError as e:
                os.remove(full_path)
                return {"status": "error", "message": f"Syntax error — file not written: {e}"}

        return {"status": "ok", "path": full_path, "bytes_written": len(content.encode("utf-8"))}
    except Exception as e:
        return {"status": "error", "message": str(e)}
