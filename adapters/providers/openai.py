import os
import json
from boros.adapters.base_adapter import BaseAdapter

class OpenaiAdapter(BaseAdapter):
    def __init__(self, config):
        self.config = config
        self.model = config.get("model", "gpt-4o")
        self.max_tokens = config.get("max_tokens", 4096)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import openai
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not set in environment")
            self._client = openai.OpenAI(api_key=api_key)
        return self._client

    def complete(self, messages: list, tools: list = None, system: str = None) -> dict:
        # Convert from Anthropic-canonical format to OpenAI format
        oai_messages = []
        if system:
            oai_messages.append({"role": "system", "content": system})

        for msg in messages:
            converted = self._to_oai_message(msg)
            # _to_oai_message returns a list for tool_result messages (one per tool)
            if isinstance(converted, list):
                oai_messages.extend(converted)
            else:
                oai_messages.append(converted)

        kwargs = {"model": self.model, "messages": oai_messages}
        if self.max_tokens:
            kwargs["max_tokens"] = self.max_tokens
        if tools:
            kwargs["tools"] = self._to_oai_tools(tools)

        response = self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        # Normalize back to Anthropic-canonical format
        content = []
        if choice.message.content:
            content.append({"type": "text", "text": choice.message.content})
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                content.append({
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": json.loads(tc.function.arguments)
                })

        stop_map = {"stop": "end_turn", "tool_calls": "tool_use", "length": "max_tokens"}
        stop_reason = stop_map.get(choice.finish_reason, "end_turn")

        return {
            "content": content,
            "stop_reason": stop_reason,
            "usage": {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            }
        }

    def _to_oai_tools(self, tools):
        """Convert Anthropic tool schemas to OpenAI function format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {"type": "object", "properties": {}})
                }
            }
            for t in tools
        ]

    def _to_oai_message(self, msg):
        """Convert Anthropic-style message to OpenAI format."""
        role = msg["role"]
        content = msg.get("content")

        # Simple string content
        if isinstance(content, str):
            return {"role": role, "content": content}

        # List of content blocks (Anthropic style)
        if isinstance(content, list):
            # Tool results → individual tool messages
            if any(b.get("type") == "tool_result" for b in content):
                # Return first tool result as a tool message; 
                # for multi-tool, we handle in caller
                results = []
                for b in content:
                    if b.get("type") == "tool_result":
                        results.append({
                            "role": "tool",
                            "tool_call_id": b["tool_use_id"],
                            "content": b.get("content", "")
                        })
                # OpenAI expects separate messages per tool result
                # Return as a list signal — handled by wrapping
                return results

            # Assistant message with tool_use blocks
            if role == "assistant":
                text_parts = [b["text"] for b in content if b.get("type") == "text"]
                tool_calls = []
                for b in content:
                    if b.get("type") == "tool_use":
                        tool_calls.append({
                            "id": b["id"],
                            "type": "function",
                            "function": {
                                "name": b["name"],
                                "arguments": json.dumps(b["input"])
                            }
                        })
                msg_out = {"role": "assistant", "content": " ".join(text_parts) if text_parts else None}
                if tool_calls:
                    msg_out["tool_calls"] = tool_calls
                return msg_out

            # User message with mixed content
            text_parts = [b.get("text", "") for b in content if b.get("type") == "text"]
            return {"role": role, "content": " ".join(text_parts)}

        return {"role": role, "content": str(content) if content else ""}
