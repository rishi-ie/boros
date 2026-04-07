import os
import subprocess

class ToolDispatcher:
    def __init__(self, sandbox_path, kernel):
        self.sandbox_path = sandbox_path
        self.kernel = kernel
        self.sandbox_scratchpad = {}

        
    def _safe_path(self, target):
        """Resolves target path while strictly preventing directory traversal escaping."""
        if not target:
            target = "temp.txt"
        target = target.replace("\\", "/")
        # Strip absolute prefixes
        if target.startswith("/"): target = target.lstrip("/")
        if len(target) > 1 and target[1] == ":": target = target[2:].lstrip("/")
        
        final_path = os.path.abspath(os.path.join(self.sandbox_path, target))
        sandbox_abs = os.path.abspath(self.sandbox_path)
        
        if not final_path.startswith(sandbox_abs):
            # Fallback for malicious or accidental escape attempts
            return os.path.abspath(os.path.join(sandbox_abs, os.path.basename(target)))
        return final_path

    def dispatch(self, tool_name, kwargs):
        try:
            # ───────────────────────────────────────────────
            # Sandbox I/O Overrides (CRITICAL FOR SAFETY)
            # ───────────────────────────────────────────────
            if tool_name == "tool_terminal":
                command = kwargs.get("command", "")
                try:
                    result = subprocess.run(
                        command,
                        shell=True,
                        cwd=self.sandbox_path,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    return {
                        "status": "ok",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode
                    }
                except subprocess.TimeoutExpired:
                    return {
                        "status": "error",
                        "error": "Command timed out after 30 seconds"
                    }
                
            elif tool_name == "tool_file_edit_diff":
                target_file = kwargs.get("target_file", "")
                filepath = self._safe_path(target_file)
                replacement_chunks = kwargs.get("replacement_chunks", [])
                
                if not os.path.exists(filepath):
                    return {"status": "error", "message": "file not found"}
                
                with open(filepath, "r") as f:
                    content = f.read()
                    
                for chunk in replacement_chunks:
                    target = chunk.get("target_content", "")
                    replacement = chunk.get("replacement_content", "")
                    if target not in content:
                        return {"status": "error", "message": f"Target content not found in file: {target[:50]}..."}
                    content = content.replace(target, replacement, 1)

                with open(filepath, "w") as f:
                    f.write(content)
                return {"status": "ok", "message": "Patch applied successfully."}

            elif tool_name == "execute_command":
                # Real subprocess execution in sandbox (same as tool_terminal)
                command = kwargs.get("command", "")
                try:
                    result = subprocess.run(
                        command,
                        shell=True,
                        cwd=self.sandbox_path,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    return {
                        "status": "ok",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode
                    }
                except subprocess.TimeoutExpired:
                    return {"status": "error", "error": "Command timed out after 30 seconds"}

            elif tool_name == "write_file":
                filepath = self._safe_path(kwargs.get("path", "temp.txt"))
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, "w") as f:
                    f.write(kwargs.get("content", ""))
                return {"status": "ok"}

            elif tool_name == "read_file":
                filepath = self._safe_path(kwargs.get("path", "temp.txt"))
                if not os.path.exists(filepath):
                    return {"status": "error", "message": "not found"}
                with open(filepath, "r") as f:
                    content = f.read()
                return {"status": "ok", "content": content}

            elif tool_name == "list_directory":
                return {"status": "ok", "files": os.listdir(self.sandbox_path)}

            elif tool_name == "scratchpad_write":
                self.sandbox_scratchpad[kwargs.get("key", "")] = kwargs.get("value", "")
                return {"status": "ok"}

            elif tool_name == "scratchpad_read":
                return {"status": "ok", "value": self.sandbox_scratchpad.get(kwargs.get("key", ""))}

            elif tool_name == "scratchpad_clear":
                if kwargs.get("key"):
                    self.sandbox_scratchpad.pop(kwargs.get("key", ""), None)
                else:
                    self.sandbox_scratchpad.clear()
                return {"status": "ok"}

            # ───────────────────────────────────────────────
            # True Boros Capabilities
            # ───────────────────────────────────────────────
            elif tool_name in self.kernel.registry:
                # Security: Block state-mutating core skills from being invoked inside sandbox
                blocked_prefixes = ("identity_", "loop_", "evolve_", "eval_", "forge_", "mission_", "comm_", "router_")
                if any(tool_name.startswith(p) for p in blocked_prefixes):
                    return {"status": "error", "error": f"Tool {tool_name} is prohibited in sandbox."}
                return self.kernel.registry[tool_name](kwargs, self.kernel)

            return {"status": "error", "error": "unknown tool"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
