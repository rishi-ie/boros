import urllib.request
import urllib.parse
import re

def research_search_engine(params: dict, kernel=None) -> dict:
    """Search the web using DuckDuckGo. Returns up to 5 results with title, link, snippet."""
    query = params.get("query", "")
    if not query:
        return {"status": "error", "message": "query required"}

    # Strategy 1: duckduckgo_search package (most reliable, no HTML parsing)
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                results.append({
                    "title":   r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "link":    r.get("href", "")
                })
        if results:
            return {"status": "ok", "query": query, "results": results, "source": "ddgs"}
    except ImportError:
        pass
    except Exception:
        pass

    # Strategy 2: DuckDuckGo Lite endpoint (simple table HTML, no JS required)
    try:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://lite.duckduckgo.com/lite/?q={encoded}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        results = _parse_ddg_lite(html)
        if results:
            return {"status": "ok", "query": query, "results": results[:5], "source": "ddg_lite"}
    except Exception as e:
        return {"status": "error", "message": f"Search failed: {e}"}

    return {"status": "ok", "query": query, "results": [], "message": "No results found"}


def _parse_ddg_lite(html: str) -> list:
    """Parse DuckDuckGo Lite HTML. Results are in a table: link rows followed by snippet rows."""
    def strip_tags(s):
        return re.sub(r"<[^>]+>", "", s).strip()

    # Match <a> tags that have class='result-link' anywhere in their attributes (any order)
    link_re = re.compile(
        r'<a\s[^>]*class=["\']result-link["\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL
    )
    # Extract href separately from the same tag (attribute order is not guaranteed)
    href_re = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)

    snippet_re = re.compile(
        r'<td[^>]+class=["\']result-snippet["\'][^>]*>(.*?)</td>',
        re.IGNORECASE | re.DOTALL
    )

    snippets = snippet_re.findall(html)

    def decode_ddg_url(href: str) -> str:
        """Extract the real URL from a DDG redirect link."""
        if "uddg=" in href:
            uddg_match = re.search(r'uddg=([^&]+)', href)
            if uddg_match:
                return urllib.parse.unquote(uddg_match.group(1))
        if href.startswith("//"):
            href = "https:" + href
        return href

    results = []
    for i, m in enumerate(link_re.finditer(html)):
        full_tag = m.group(0)
        title    = strip_tags(m.group(1)).strip()
        href_m   = href_re.search(full_tag)
        raw_href = href_m.group(1) if href_m else ""
        href     = decode_ddg_url(raw_href)
        snippet  = strip_tags(snippets[i]) if i < len(snippets) else ""

        # Skip ads, nav links, and empty/short titles
        if not title or len(title) < 5:
            continue
        if "duckduckgo.com" in href and "uddg=" not in raw_href:
            continue  # internal DDG navigation link

        results.append({"title": title, "link": href, "snippet": snippet})

    return results
