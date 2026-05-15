"""
MiniMax Adapter — REST API for MiniMax LLM.

MiniMax API: https://api.minimax.chat/v1/text/chatcompletion_v2
"""

import os
import json
import time
import urllib.request
import urllib.error
import uuid
from adapters.base_adapter import BaseAdapter


class MinimaxAdapter(BaseAdapter):
    """MiniMax adapter via REST API."""

    def __init__(self, config):
        self.config = config
        self.model = config.get("model", "MiniMax-Text-01")
        self.max_tokens = config.get("max_tokens", 4096)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            api_key = os.environ.get("MINIMAX_API_KEY")
            if not api_key:
                raise RuntimeError("MINIMAX_API_KEY not set in environment")
            self._client = {
                "api_key": api_key,
                "base_url": "https://api.minimax.chat/v1"
            }
        return self._client

    def complete(self, messages: list, tools: list = None, system: str = None) -> dict:
        api_key = os.environ.get("MINIMAX_API_KEY")
        if not api_key:
            raise RuntimeError("MINIMAX_API_KEY not set in environment")

        # Build messages with system instruction merged
        oai_messages = []
        if system:
            oai_messages.append({"role": "system", "content": system})

        for msg in messages:
            # Skip system (already handled above)
            if msg["role"] == "system":
                continue

            role = msg["role"]
            content_data = msg.get("content", "")

            # Handle list content (Anthropic style)
            if isinstance(content_data, list):
                text_parts = []
                for block in content_data:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_result":
                        # MiniMax doesn't use tool_use blocks in same way
                        # Convert to simple content
                        tool_content = block.get("content", "")
                        if tool_content:
                            text_parts.append(f"[TOOL RESULT: {tool_content}]")

                msg_content = " ".join(text_parts) if text_parts else ""
                if not msg_content and any(b.get("type") == "tool_result" for b in content_data):
                    # If only tool results with empty content, add placeholder
                    msg_content = "[tool_result]"

                if role == "assistant":
                    # Assistant might have content + function_call later
                    # For now, just add the text content
                    if msg_content:
                        oai_messages.append({"role": role, "content": msg_content})
                    else:
                        oai_messages.append({"role": role, "content": ""})
                else:
                    oai_messages.append({"role": role, "content": msg_content or ""})
            else:
                # Simple string content
                oai_messages.append({"role": role, "content": str(content_data) if content_data else ""})

        # Build payload
        payload = {
            "model": self.model,
            "messages": oai_messages,
            "max_tokens": self.max_tokens,
        }

        # Handle tools if supported
        if tools:
            func_decls = []
            for t in tools:
                schema = {
                    "name": t.get("name"),
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {})
                }
                func_decls.append(schema)
            if func_decls:
                payload["tools"] = [{"type": "function", "function": f} for f in func_decls]

        # Make API call
        url = f"{self.client['base_url']}/text/chatcompletion_v2"
        data_bytes = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )

        data = None
        last_error = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read())
                break
            except urllib.error.HTTPError as e:
                last_error = e
                if e.code == 429:
                    wait = (2 ** attempt) * 5
                    print(f"[MiniMax] Rate limited (429). Retrying in {wait}s (attempt {attempt+1}/3)...")
                    time.sleep(wait)
                else:
                    raise
            except Exception as e:
                last_error = e
                if attempt < 2:
                    time.sleep(2 ** attempt * 2)
                else:
                    raise

        if data is None:
            raise RuntimeError(f"MiniMax API failed after 3 attempts: {last_error}")

        # Parse response
        output_content = []
        stop_reason = "end_turn"

        choice = data.get("choices", [{}])[0] if data.get("choices") else {}
        finish = choice.get("finish_reason", "")

        if finish == "length":
            stop_reason = "max_tokens"
        elif finish == "tool_calls":
            stop_reason = "tool_use"

        message = choice.get("message", {})
        msg_content = message.get("content", "")

        if msg_content:
            output_content.append({"type": "text", "text": msg_content})

        # Handle tool calls
        tool_calls = message.get("tool_calls", [])
        for tc in tool_calls:
            call_id = tc.get("id", f"call_{uuid.uuid4().hex[:8]}")
            func = tc.get("function", {})
            fname = func.get("name", "unknown")
            fargs = func.get("arguments", {})

            if isinstance(fargs, str):
                try:
                    fargs = json.loads(fargs)
                except json.JSONDecodeError:
                    fargs = {}

            output_content.append({
                "type": "tool_use",
                "id": call_id,
                "name": fname,
                "input": fargs
            })
            stop_reason = "tool_use"

        usage = data.get("usage", {})

        return {
            "content": output_content,
            "stop_reason": stop_reason,
            "usage": {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0)
            }
        }

    @property
    def supports_tools(self) -> bool:
        """MiniMax supports function calling."""
        return True