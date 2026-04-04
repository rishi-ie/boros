
import os, json, datetime
def research_archive_source(params: dict, kernel=None) -> dict:
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    url = params.get("url", "")
    tag = params.get("tag", "untagged")
    import urllib.request, uuid
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Boros/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode("utf-8", errors="replace")
        archive_dir = os.path.join(boros_dir, "memory", "experiences")
        os.makedirs(archive_dir, exist_ok=True)
        entry_id = f"src-{uuid.uuid4().hex[:8]}"
        with open(os.path.join(archive_dir, f"{entry_id}.json"), "w") as f:
            json.dump({"id": entry_id, "type": "web_source", "url": url, "tag": tag, "content": content[:5000], "timestamp": datetime.datetime.utcnow().isoformat() + "Z"}, f, indent=2)
        return {"status": "ok", "entry_id": entry_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}
