
import os, json, glob
def memory_page_in(params: dict, kernel=None) -> dict:
    """Load data from long-term memory into context."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    source = params.get("source", "scores")
    limit = params.get("limit", 10)
    data = []
    if source == "scores":
        score_file = os.path.join(boros_dir, "memory", "score_history.jsonl")
        if os.path.exists(score_file):
            if os.path.getsize(score_file) > 0:
                with open(score_file) as f:
                    lines = f.readlines()
                for line in lines[-limit:]:
                    if line.strip():
                        try:
                            data.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            if kernel:
                                kernel.log_error(f"Memory: Failed to decode JSON from score_history.jsonl: {e} in line: {line.strip()}")
                            else:
                                print(f"Memory: Failed to decode JSON from score_history.jsonl: {e} in line: {line.strip()}")
                        except Exception as e:
                            if kernel:
                                kernel.log_error(f"Memory: An unexpected error occurred while reading score_history.jsonl: {e} in line: {line.strip()}")
                            else:
                                print(f"Memory: An unexpected error occurred while reading score_history.jsonl: {e} in line: {line.strip()}")
            else:
                if kernel:
                    kernel.log_warn("Memory: score_history.jsonl exists but is empty.")
                else:
                    print("Memory: score_history.jsonl exists but is empty.")
        else:
            if kernel:
                kernel.log_warn("Memory: score_history.jsonl not found.")
            else:
                print("Memory: score_history.jsonl not found.")
    elif source == "experiences":
        exp_dir = os.path.join(boros_dir, "memory", "experiences")
        if os.path.isdir(exp_dir) and len(os.listdir(exp_dir)) > 0:
            for f in sorted(glob.glob(os.path.join(exp_dir, "*.json")), key=os.path.getmtime, reverse=True)[:limit]:
                try:
                    with open(f) as fh: data.append(json.load(fh))
                except: pass
    elif source == "evolution_records":
        rec_dir = os.path.join(boros_dir, "memory", "evolution_records")
        if os.path.isdir(rec_dir):
            for f in sorted(glob.glob(os.path.join(rec_dir, "*.json")), key=os.path.getmtime, reverse=True)[:limit]:
                try:
                    with open(f) as fh: data.append(json.load(fh))
                except: pass
    elif source == "sessions":
        sess_dir = os.path.join(boros_dir, "memory", "sessions")
        if os.path.isdir(sess_dir):
            for f in sorted(glob.glob(os.path.join(sess_dir, "*.json")), key=os.path.getmtime, reverse=True)[:limit]:
                try:
                    with open(f) as fh: data.append(json.load(fh))
                except: pass
    elif source == "session_buffer":
        sess_file = os.path.join(boros_dir, "memory", "sessions", "current_buffer.json")
        if os.path.exists(sess_file):
            try:
                with open(sess_file) as f:
                    data.append(json.load(f))
            except: pass
    return {"status": "ok", "source": source, "entries": data, "count": len(data)}
