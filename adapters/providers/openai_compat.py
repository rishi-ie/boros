import os
import json
from adapters.base_adapter import BaseAdapter

class OpenaiCompatAdapter(BaseAdapter):
    """OpenAI-compatible adapter for providers like Together, Groq, etc."""

    def __init__(self, config):
        self.config = config
        self.model = config.get("model", "")
        self.max_tokens = config.get("max_tokens", 4096)
        self.base_url = config.get("base_url", "")
        self.api_key_env = config.get("api_key_env", "OPENAI_COMPAT_API_KEY")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import openai
            api_key = os.environ.get(self.api_key_env, "")
            if not api_key:
                raise RuntimeError(f"{self.api_key_env} not set in environment")
            self._client = openai.OpenAI(api_key=api_key, base_url=self.base_url)
        return self._client

    def complete(self, messages: list, tools: list = None, system: str = None) -> dict:
        oai_messages = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        for msg in messages:
            if isinstance(msg.get("content"), str):
                oai_messages.append(msg)
            else:
                oai_messages.append({"role": msg["role"], "content": str(msg.get("content", ""))})

        kwargs = {"model": self.model, "messages": oai_messages}
        if self.max_tokens:
            kwargs["max_tokens"] = self.max_tokens

        response = self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        content = []
        if choice.message.content:
            content.append({"type": "text", "text": choice.message.content})

        return {
            "content": content,
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": getattr(response.usage, "prompt_tokens", 0),
                "output_tokens": getattr(response.usage, "completion_tokens", 0)
            }
        }

    @property
    def supports_tools(self):
        return False
