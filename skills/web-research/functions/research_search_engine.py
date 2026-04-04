import urllib.request
import urllib.parse
from html.parser import HTMLParser

class DDGParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self.in_result_link = False
        self.in_result_snippet = False
        self.current_result = {}
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'a' and 'class' in attrs_dict and 'result__a' in attrs_dict['class']:
            self.in_result_link = True
            self.current_result['link'] = attrs_dict.get('href', '')
        if tag == 'a' and 'class' in attrs_dict and 'result__snippet' in attrs_dict['class']:
            self.in_result_snippet = True
            
    def handle_endtag(self, tag):
        if tag == 'a' and self.in_result_link:
            self.in_result_link = False
            if self.current_result.get('title') and self.current_result.get('snippet'):
                self.results.append(self.current_result)
            self.current_result = {}
        if tag == 'a' and self.in_result_snippet:
            self.in_result_snippet = False

    def handle_data(self, data):
        if self.in_result_link and not self.current_result.get('title'):
            self.current_result['title'] = data.strip()
        if self.in_result_snippet:
            self.current_result['snippet'] = self.current_result.get('snippet', '') + data.strip()

def research_search_engine(params: dict, kernel=None) -> dict:
    query = params.get("query", "")
    if not query:
        return {"status": "error", "message": "query required"}
        
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
        parser = DDGParser()
        parser.feed(html)
        
        return {"status": "ok", "query": query, "results": parser.results[:5]}
    except Exception as e:
         return {"status": "error", "message": f"Search failed: {e}"}
