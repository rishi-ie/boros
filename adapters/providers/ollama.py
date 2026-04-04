import json
import urllib.request
from boros.adapters.base_adapter import BaseAdapter

class OllamaAdapter(BaseAdapter):
    """Local Ollama adapter — no API key needed, uses HTTP."""

    def __init__(self, config):
        self.config = config
        self.model = config.get("model", "llama3")
        self.base_url = config.get("base_url", "http://localhost:11434")

    def complete(self, messages: list, tools: list = None, system: str = None) -> dict:
        ollama_messages = []
        if system:
            ollama_messages.append({"role": "system", "content": system})
        for msg in messages:
            if isinstance(msg.get("content"), str):
                ollama_messages.append(msg)
            else:
                ollama_messages.append({"role": msg["role"], "content": str(msg.get("content", ""))})

        payload = json.dumps({"model": self.model, "messages": ollama_messages, "stream": False}).encode()
        req = urllib.request.Request(f"{self.base_url}/api/chat", data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())

        text = data.get("message", {}).get("content", "")
        return {
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 0, "output_tokens": 0}
        }

    @property
    def supports_tools(self):
        return False
