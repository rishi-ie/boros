
import os
import py_compile

def forge_apply_diff(params: dict, kernel=None) -> dict:
    """Apply a diff to a skill's function file using find-and-replace."""
    target_file = params.get("target_file", "")
    replacement_chunks = params.get("replacement_chunks", [])

    if not target_file:
        return {"status": "error", "message": "target_file required"}
    if not os.path.exists(target_file):
        return {"status": "error", "message": f"File not found: {target_file}"}

    try:
        with open(target_file, "r") as f:
            original_content = f.read()
            
        content = original_content

        for chunk in replacement_chunks:
            target = chunk.get("target_content", "")
            replacement = chunk.get("replacement_content", "")
            
            if target not in content:
                return {"status": "error", "message": f"Target content not found: {target[:60]}..."}
            content = content.replace(target, replacement, 1)

        with open(target_file, "w") as f:
            f.write(content)
            
        if target_file.endswith(".py"):
            try:
                py_compile.compile(target_file, doraise=True)
            except py_compile.PyCompileError as build_err:
                with open(target_file, "w") as f:
                    f.write(original_content)
                return {
                    "status": "error",
                    "message": "Syntax validation failed. Diff application aborted.",
                    "details": str(build_err)
                }

        return {"status": "ok", "message": f"Applied {len(replacement_chunks)} chunks to {target_file}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
