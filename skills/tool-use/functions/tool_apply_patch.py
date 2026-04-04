import os, tempfile, subprocess  
  
def tool_apply_patch(params: dict, kernel=None) -> dict:
    """Apply a diff/patch to a file using git apply."""  
    diff_content = params.get("diff_content")  
    target_file = params.get("target_file")  
  
    if not diff_content or not target_file:  
        return {"status": "error", "message": "diff_content and target_file are required."}  
  
    # We need to ensure the target directory exists for git to work with it  
    target_dir = os.path.dirname(target_file)  
    if not os.path.exists(target_dir):  
        os.makedirs(target_dir)  
  
    # Create a temporary patch file  
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".patch") as patch_file:  
        patch_file.write(diff_content)  
        patch_filename = patch_file.name  
  
    try:  
        # Use subprocess to run git apply  
        result = subprocess.run(  
            ["git", "apply", "--unidiff-zero", "--inaccurate-eof", patch_filename],  
            check=True, capture_output=True, text=True  
        )  
        return {"status": "ok", "message": "Patch applied successfully.", "stdout": result.stdout}  
    except subprocess.CalledProcessError as e:  
        return {"status": "error", "message": "Failed to apply patch.", "stderr": e.stderr}  
    finally:  
        # Clean up the temporary patch file  
        os.remove(patch_filename) 
