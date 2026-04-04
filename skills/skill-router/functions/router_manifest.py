
import json
def router_manifest(params: dict, kernel=None) -> dict:
    if kernel:
        return {"status": "ok", "manifest": kernel.manifest}
    return {"status": "ok", "manifest": {}}
