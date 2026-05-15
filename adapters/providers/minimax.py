"""
MiniMax Adapter — Anthropic-compatible API for MiniMax M2.7 and MiniMax-Text-01.

Supports both:
- MiniMax-M2.7 (Anthropic-compatible, supports thinking blocks)
- MiniMax-Text-01 (via /v1/text/chatcompletion_v2)

Docs: https://platform.minimax.io/docs/llms.txt
"""

import os
import json
import time
import urllib.request
import urllib.error
import uuid
from typing import Any
from adapters.base_adapter import BaseAdapter


class MinimaxAdapter(BaseAdapter):
    """MiniMax adapter via Anthropic-compatible API (for M2.7) or REST API (for Text-01)."""

    # Models that use Anthropic-compatible API
    ANTHROPIC_COMPAT_MODELS = {"MiniMax-M2.7", "MiniMax-M2"}

    def __init__(self, config: dict):
        self.config = config
        self.model = config.get("model", "MiniMax-M2.7")
        self.max_tokens = config.get("max_tokens", 8192)
        self._client = None

    @property
    def supports_tools(self) -> bool:
        """Whether this model supports tool use."""
        # M2.7 supports tools, Text-01 as well
        return True

    def complete(self, messages: list, tools: list = None, system: str = None) -> dict:
        api_key = os.environ.get("MINIMAX_API_KEY")
        if not api_key:
            raise RuntimeError("MINIMAX_API_KEY not set in environment")

        if self.model in self.ANTHROPIC_COMPAT_MODELS:
            return self._complete_anthropic_compat(api_key, messages, tools, system)
        else:
            return self._complete_rest(api_key, messages, tools, system)

    def _complete_anthropic_compat(self, api_key: str, messages: list,
                                    tools: list | None, system: str | None) -> dict:
        """Use Anthropic-compatible API (for M2.7)."""
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("Install anthropic: pip install anthropic")

        client = anthropic.Anthropic(
            base_url="https://api.minimax.io/anthropic",
            api_key=api_key,
        )

        # Build messages in Anthropic format
        oai_messages = []
        if system:
            oai_messages.append({"role": "user", "content": f"[SYSTEM: {system}]"})

        for msg in messages:
            if msg["role"] == "system":
                continue

            role = msg["role"]
            content = msg.get("content", "")

            # Handle list content (from base adapter)
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        tool_result = block.get("content", "")
                        text_parts.append(f"[TOOL: {block.get('name')} → {tool_result}]")
                content = " ".join(text_parts) if text_parts else ""

            oai_messages.append({"role": role, "content": content or ""})

        # Build tool use for Anthropic format
        anthropic_tools = None
        if tools:
            anthropic_tools = []
            for t in tools:
                anthropic_tools.append({
                    "name": t.get("name"),
                    "description": t.get("description", ""),
                    "input_schema": t.get("input_schema", {"type": "object", "properties": {}}),
                })

        # Make the call
        try:
            message = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system or "You are a helpful AI assistant.",
                messages=[{"role": m["role"], "content": m["content"]} for m in oai_messages],
                tools=anthropic_tools,
            )
        except Exception as e:
            raise RuntimeError(f"MiniMax M2.7 API failed: {e}")

        # Parse response
        output_content = []
        stop_reason = "end_turn"

        for block in message.content:
            if block.type == "text":
                output_content.append({"type": "text", "text": block.text})
            elif block.type == "thinking":
                # Skip thinking blocks (not returned as tool results)
                pass
            elif block.type == "tool_use":
                output_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
                stop_reason = "tool_use"

        # Check if model used a tool
        if hasattr(message, "stop_reason"):
            if message.stop_reason == "tool_use":
                stop_reason = "tool_use"
            elif message.stop_reason == "max_tokens":
                stop_reason = "max_tokens"

        usage = dict(message.usage) if hasattr(message, "usage") else {}

        return {
            "content": output_content,
            "stop_reason": stop_reason,
            "usage": {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            },
        }

    def _complete_rest(self, api_key: str, messages: list,
                       tools: list | None, system: str | None) -> dict:
        """Use REST API (for MiniMax-Text-01 and other text models)."""
        # Build messages
        oai_messages = []
        if system:
            oai_messages.append({"role": "system", "content": system})

        for msg in messages:
            if msg["role"] == "system":
                continue

            role = msg["role"]
            content_data = msg.get("content", "")

            if isinstance(content_data, list):
                text_parts = []
                for block in content_data:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_result":
                        tool_content = block.get("content", "")
                        if tool_content:
                            text_parts.append(f"[TOOL RESULT: {tool_content}]")

                msg_content = " ".join(text_parts) if text_parts else ""
                if not msg_content and any(b.get("type") == "tool_result" for b in content_data):
                    msg_content = "[tool_result]"

                oai_messages.append({"role": role, "content": msg_content or ""})
            else:
                oai_messages.append({"role": role, "content": str(content_data) if content_data else ""})

        # Build payload
        payload = {
            "model": self.model,
            "messages": oai_messages,
            "max_tokens": self.max_tokens,
        }

        # Handle tools
        if tools:
            func_decls = []
            for t in tools:
                schema = {
                    "name": t.get("name"),
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {}),
                }
                func_decls.append(schema)
            if func_decls:
                payload["tools"] = [{"type": "function", "function": f} for f in func_decls]

        # Make API call
        url = f"https://api.minimax.chat/v1/text/chatcompletion_v2"
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
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
                    wait = (2**attempt) * 5
                    print(f"[MiniMax] Rate limited (429). Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise
            except Exception as e:
                last_error = e
                if attempt < 2:
                    time.sleep(2**attempt * 2)
                else:
                    raise

        if data is None:
            raise RuntimeError(f"MiniMax REST API failed after 3 attempts: {last_error}")

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
                "input": fargs,
            })
            stop_reason = "tool_use"

        usage = data.get("usage", {})

        return {
            "content": output_content,
            "stop_reason": stop_reason,
            "usage": {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
            },
        }