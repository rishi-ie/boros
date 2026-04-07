
import os, json, glob
def memory_page_in(params: dict, kernel=None) -> dict:
    """Load data from long-term memory into context."""
    boros_dir = str(kernel.boros_root) if kernel else os.getcwd()
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
                            print(f"Memory: Failed to decode JSON from score_history.jsonl: {e}")
                        except Exception as e:
                            print(f"Memory: Unexpected error reading score_history.jsonl: {e}")
            else:
                print("Memory: score_history.jsonl exists but is empty.")
        else:
            print("Memory: score_history.jsonl not found.")
    elif source == "experiences":
        exp_dir = os.path.join(boros_dir, "memory", "experiences")
        if os.path.isdir(exp_dir):
            for f in sorted(glob.glob(os.path.join(exp_dir, "*.json")), key=os.path.getmtime, reverse=True)[:limit]:
                try:
                    with open(f) as fh:
                        data.append(json.load(fh))
                except (json.JSONDecodeError, OSError) as e:
                    print(f"Memory: Error reading experience file {f}: {e}")
    elif source == "evolution_records":
        rec_dir = os.path.join(boros_dir, "memory", "evolution_records")
        if os.path.isdir(rec_dir):
            for f in sorted(glob.glob(os.path.join(rec_dir, "*.json")), key=os.path.getmtime, reverse=True)[:limit]:
                try:
                    with open(f) as fh:
                        data.append(json.load(fh))
                except (json.JSONDecodeError, OSError) as e:
                    print(f"Memory: Error reading evolution record {f}: {e}")
    elif source == "sessions":
        sess_dir = os.path.join(boros_dir, "memory", "sessions")
        if os.path.isdir(sess_dir):
            for f in sorted(glob.glob(os.path.join(sess_dir, "*.json")), key=os.path.getmtime, reverse=True)[:limit]:
                try:
                    with open(f) as fh:
                        data.append(json.load(fh))
                except (json.JSONDecodeError, OSError) as e:
                    print(f"Memory: Error reading session file {f}: {e}")
    elif source == "session_buffer":
        sess_file = os.path.join(boros_dir, "memory", "sessions", "current_buffer.json")
        if os.path.exists(sess_file):
            try:
                with open(sess_file) as f:
                    data.append(json.load(f))
            except (json.JSONDecodeError, OSError) as e:
                print(f"Memory: Error reading session buffer: {e}")
    return {"status": "ok", "source": source, "entries": data, "count": len(data)}
