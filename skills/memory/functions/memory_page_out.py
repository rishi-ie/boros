
import os, json
def memory_page_out(params: dict, kernel=None) -> dict:
    """Write key-value data to the current session buffer."""
    key = params.get("key", "")
    value = params.get("value", "")
    boros_dir = str(kernel.boros_root) if kernel else os.getcwd()
    sess_dir = os.path.join(boros_dir, "memory", "sessions")
    os.makedirs(sess_dir, exist_ok=True)
    sess_file = os.path.join(sess_dir, "current_buffer.json")
    buffer = {}
    if os.path.exists(sess_file):
        with open(sess_file) as f:
            buffer = json.load(f)
    buffer[key] = value
    with open(sess_file, "w") as f:
        json.dump(buffer, f, indent=2)
    return {"status": "ok", "key": key}
