
import os, json
def context_get_manifest(params: dict, kernel=None) -> dict:
    boros_dir = str(kernel.boros_root) if kernel else __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))))
    mf = os.path.join(boros_dir, "session", "context_manifest.json")
    if os.path.exists(mf):
        with open(mf) as f:
            return {"status": "ok", "manifest": json.load(f)}
    return {"status": "ok", "manifest": {}, "message": "No context loaded yet. Call context_load first."}
