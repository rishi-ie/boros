
import os, py_compile
def forge_validate(params: dict, kernel=None) -> dict:
    """Validate a skill's Python files for syntax errors."""
    boros_dir = str(kernel.boros_root) if kernel else __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))))
    skill_name = params.get("target", params.get("skill_name", ""))
    if not skill_name:
        return {"status": "error", "message": "skill_name required"}

    # Normalize: if a full path was passed (e.g. "skills/memory/functions/foo.py"), extract skill name
    normalized = skill_name.replace("\\", "/")
    parts = normalized.split("/")
    if len(parts) >= 2 and parts[0] == "skills":
        skill_name = parts[1]

    func_dir = os.path.join(boros_dir, "skills", skill_name, "functions")
    if not os.path.isdir(func_dir):
        return {"status": "error", "message": f"Functions dir not found: {func_dir}"}

    errors = []
    valid = []
    for fname in os.listdir(func_dir):
        if fname.endswith(".py"):
            fpath = os.path.join(func_dir, fname)
            try:
                py_compile.compile(fpath, doraise=True)
                valid.append(fname)
            except py_compile.PyCompileError as e:
                errors.append({"file": fname, "error": str(e)})

    return {
        "status": "ok" if not errors else "error",
        "valid_files": valid,
        "errors": errors,
        "message": f"{len(valid)} files valid, {len(errors)} errors" 
    }
