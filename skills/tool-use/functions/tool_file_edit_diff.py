import os
import py_compile

def tool_file_edit_diff(params: dict, kernel=None) -> dict:
    target_file = params.get("target_file")
    replacement_chunks = params.get("replacement_chunks", [])
    
    if not target_file: return {"status": "error", "message": "target_file required"}
    if not os.path.exists(target_file): return {"status": "error", "message": "file not found"}
    
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
