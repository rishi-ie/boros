import json
import os

CORE_MEMORY_FILE = "core_memory.json"

def core_memory_append(args, context):
    """
    Appends text to a specific block in the Core Memory file.
    Args:
        block (str): "persona_status" or "director_dossier"
        content (str): The content to append to the block.
    """
    block = args.get("block")
    content = args.get("content")
    
    if not block or not content:
        return {"status": "error", "message": "Missing 'block' or 'content' in arguments."}
        
    workspace_root = context.get("workspace_root", ".")
    file_path = os.path.join(workspace_root, CORE_MEMORY_FILE)
        
    if not os.path.exists(file_path):
        return {"status": "error", "message": f"{CORE_MEMORY_FILE} not found at {file_path}."}
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if block not in data:
            return {"status": "error", "message": f"Block '{block}' not found in core memory."}
            
        data[block] += "\n" + content
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
        return {"status": "ok", "message": f"Successfully appended to {block}."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
