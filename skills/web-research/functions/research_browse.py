
import urllib.request, html
def research_browse(params: dict, kernel=None) -> dict:
    url = params.get("url", "")
    if not url:
        return {"status": "error", "message": "url required"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Boros/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode("utf-8", errors="replace")[:10000]
        return {"status": "ok", "content": content, "url": url}
    except Exception as e:
        return {"status": "error", "message": str(e)}
