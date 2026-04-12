import os
import json
import time
import urllib.request
import urllib.error
import uuid
from adapters.base_adapter import BaseAdapter

class GeminiAdapter(BaseAdapter):
    """Google Gemini adapter via REST API."""

    def __init__(self, config):
        self.config = config
        self.model = config.get("model", "gemini-1.5-pro")

    def complete(self, messages: list, tools: list = None, system: str = None) -> dict:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set in environment")

        payload = {}
        
        # 1. System Instruction
        if system:
            payload["systemInstruction"] = {
                "parts": [{"text": system}]
            }

        # 2. Tools array
        if tools:
            # Anthropic tools -> Gemini functionDeclarations
            func_decls = []
            for t in tools:
                schema = {
                    "name": t.get("name"),
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {})
                }
                func_decls.append(schema)
            if func_decls:
                payload["tools"] = [{"functionDeclarations": func_decls}]

        # 3. Compile contents & track function IDs
        tool_id_to_name = {}
        contents = []
        
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            parts = []
            
            content_data = msg.get("content", "")
            if isinstance(content_data, list):
                for block in content_data:
                    if block.get("type") == "text":
                        parts.append({"text": block.get("text", "")})
                    elif block.get("type") == "tool_use":
                        tool_id_to_name[block["id"]] = block["name"]
                        parts.append({
                            "functionCall": {
                                "name": block["name"],
                                "args": block.get("input", {})
                            }
                        })
                    elif block.get("type") == "tool_result":
                        tid = block["tool_use_id"]
                        fname = tool_id_to_name.get(tid, "unknown")
                        # Gemini requires functionResponse response to be an object
                        res_val = block.get("content")
                        if isinstance(res_val, str):
                            try:
                                # Attempt to parse JSON string back to dict so it's clean
                                parsed = json.loads(res_val)
                                res_val = parsed
                            except json.JSONDecodeError:
                                pass
                        
                        parts.append({
                            "functionResponse": {
                                "name": fname,
                                "response": {"result": res_val}
                            }
                        })
            else:
                parts.append({"text": str(content_data)})
                
            contents.append({"role": role, "parts": parts})
            
        payload["contents"] = contents

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={api_key}"
        data_bytes = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})

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
                    print(f"[Gemini] Rate limited (429). Retrying in {wait}s (attempt {attempt+1}/3)...")
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
            raise RuntimeError(f"Gemini API failed after 3 attempts: {last_error}")

        # 4. Parse the output
        output_content = []
        stop_reason = "end_turn"
        
        if "candidates" in data and data["candidates"]:
            cand = data["candidates"][0]
            finish_reason = cand.get("finishReason", "STOP")
            if finish_reason == "MAX_TOKENS":
                stop_reason = "max_tokens"
            elif finish_reason != "STOP":
                stop_reason = finish_reason
                
            parts = cand.get("content", {}).get("parts", [])
            for p in parts:
                if "text" in p:
                    output_content.append({"type": "text", "text": p["text"]})
                elif "functionCall" in p:
                    fc = p["functionCall"]
                    call_id = f"call_{str(uuid.uuid4())[:8]}"
                    output_content.append({
                        "type": "tool_use",
                        "id": call_id,
                        "name": fc["name"],
                        "input": fc.get("args", {})
                    })
                    stop_reason = "tool_use"
        
        metadata = data.get("usageMetadata", {})
        usage = {
            "input_tokens": metadata.get("promptTokenCount", 0),
            "output_tokens": metadata.get("candidatesTokenCount", 0)
        }

        return {
            "content": output_content,
            "stop_reason": stop_reason,
            "usage": usage
        }

    @property
    def supports_tools(self):
        return True
