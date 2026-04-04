import threading
import time
import json
import os
import re
from pathlib import Path
from prompt_toolkit import PromptSession, print_formatted_text, HTML
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

# Helper to safely escape text for HTML display
def escape(t):
    return str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

class DirectorInterface:
    def __init__(self, kernel):
        self.kernel = kernel
        self.boros_root = kernel.boros_root
        self.pause_requested = False

        # Ensure directories
        self.commands_dir = self.boros_root / "commands"
        self.commands_dir.mkdir(parents=True, exist_ok=True)
        self.pending_file = self.commands_dir / "pending.json"
        if not self.pending_file.exists():
            with open(self.pending_file, "w") as f:
                json.dump({"pending": []}, f)

        self.logs_dir = self.boros_root / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.cycles_log = self.logs_dir / "cycles.log"
        if not self.cycles_log.exists():
            self.cycles_log.touch()

    def log_to_console(self, msg):
        """Callback for agent loop to print to prompt_toolkit console."""
        # Log purely to file first
        try:
            with open(self.cycles_log, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

        if not msg:
            return

        # Prevent previous ansi colors bleeding into rich or breaking prompt toolkit
        msg = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', str(msg))
        msg = msg.strip()

        if not msg:
            return

        def format_result(text, max_len=150):
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    if data.get("status") == "error" or ("returncode" in data and data.get("returncode", 0) != 0):
                        err = data.get("error", data.get("stderr", "Unknown error"))
                        return f"<b><ansired>Error:</ansired></b> {escape(str(err).strip()[:max_len])}", True
                    else:
                        out = data.get("stdout", data.get("output", data.get("result", "")))
                        if isinstance(out, (dict, list)):
                            out = json.dumps(out)
                        if not out and data.get("status") == "ok":
                            out = "Success (No output)"
                        return escape(str(out).strip()[:max_len].replace("\n", " ")), False
            except Exception:
                pass
            text = text.replace('\n', ' ')
            return escape(text[:max_len] + ("..." if len(text) > max_len else "")), False

        if msg.startswith("[CYCLE]"):
            clean_msg = escape(msg.replace('[CYCLE]', '').strip())
            print_formatted_text(HTML(f"\n<b><ansimagenta>🔄 {clean_msg}</ansimagenta></b>"))
        elif msg.startswith("[ERROR]"):
            clean_msg = escape(msg.replace('[ERROR]', '').strip())
            print_formatted_text(HTML(f"<b><ansired>❌ {clean_msg}</ansired></b>"))
        elif msg.startswith("[BOROS]"):
            text = escape(msg[7:].strip())
            print_formatted_text(HTML(f"<ansicyan>🧠 Boros:</ansicyan> <b><ansiwhite>{text}</ansiwhite></b>"))
        elif msg.startswith("[BOROS EXECUTION]"):
            text = escape(msg[17:].strip())
            print_formatted_text(HTML(f"<ansicyan>🚀 Executing:</ansicyan> <b><ansiwhite>{text}</ansiwhite></b>"))
        elif msg.startswith("[TOKENS]"):
            text = escape(msg[8:].strip())
            print_formatted_text(HTML(f"<style fg=\"ansiwhite\">📊 {text}</style>"))
        elif msg.startswith("[TOOL] →"):
            text = escape(msg[8:].strip())
            print_formatted_text(HTML(f"<ansiyellow>⚡ Calling Tool:</ansiyellow> <style fg=\"#8a8a8a\">{text}</style>"))
        elif msg.startswith("[TOOL] ←"):
            text = msg[8:].strip()
            preview, is_error = format_result(text)
            if is_error:
                print_formatted_text(HTML(f"<b><ansired>✗ Tool Failed:</ansired></b> <style fg=\"#ff8787\">{preview}</style>"))
            else:
                print_formatted_text(HTML(f"<b><ansigreen>✔ Tool Finished:</ansigreen></b> <style fg=\"#87ff87\">{preview}</style>"))
        elif msg.startswith("[EXEC TOOL] →"):
            text = escape(msg[13:].strip())
            print_formatted_text(HTML(f"<ansiyellow>⚡ Executing:</ansiyellow> <style fg=\"#8a8a8a\">{text}</style>"))
        elif msg.startswith("[EXEC TOOL] ←"):
            text = msg[13:].strip()
            preview, is_error = format_result(text)
            if is_error:
                print_formatted_text(HTML(f"<b><ansired>✗ Exec Failed:</ansired></b> <style fg=\"#ff8787\">{preview}</style>"))
            else:
                print_formatted_text(HTML(f"<b><ansigreen>✔ Exec Finished:</ansigreen></b> <style fg=\"#87ff87\">{preview}</style>"))
        elif "📝 [PROPOSAL CREATED]" in msg:
            print_formatted_text(HTML("<b><ansicyan> 📝 PROPOSAL CREATED </ansicyan></b>"))
        elif "⚙️ [CODE MUTATION]" in msg:
            print_formatted_text(HTML("<b><ansiyellow> ⚙️ CODE MUTATED </ansiyellow></b>"))
        elif msg.startswith("[+]"):
            print_formatted_text(HTML(f"<ansigreen>{escape(msg[:150])}</ansigreen>"))
        elif msg.startswith("[-]"):
            print_formatted_text(HTML(f"<ansired>{escape(msg[:150])}</ansired>"))
        elif msg.startswith("---") or msg.startswith("============="):
            pass
        elif msg.startswith("director>"):
            pass
        elif msg.startswith("[RATE_LIMIT]"):
            print_formatted_text(HTML(f"<b><ansiyellow>⏳ {escape(msg)}</ansiyellow></b>"))
        else:
            if "Command failed with return code" in msg:
                print_formatted_text(HTML(f"<ansired>{escape(msg.strip())}</ansired>"))
            else:
                out = msg.strip().replace('\n', ' ')
                if len(out) > 150:
                    out = out[:147] + "..."
                print_formatted_text(HTML(f"<style fg=\"#8a8a8a\">{escape(out)}</style>"))

    def run_kernel_loop(self):
        """Run the actual agentic evolution loop in background."""
        print_formatted_text(HTML("<b><ansigreen>Starting Boros evolution loop...</ansigreen></b>"))

        if self.kernel.evolution_llm is None:
            print_formatted_text(HTML("<b><ansired>Cannot start loop: No evolution LLM adapter loaded.</ansired></b>"))
            print_formatted_text(HTML("<ansiyellow>Set ANTHROPIC_API_KEY in environment or boros/.env, then restart.</ansiyellow>"))
            return

        from boros.agent_loop import AgentLoop
        loop = AgentLoop(self.kernel, log_callback=self.log_to_console)

        try:
            loop.run_continuous(
                should_pause=lambda: self.pause_requested,
                on_cycle_complete=lambda num, tc: print_formatted_text(HTML(
                    f"<ansigreen>✔ Cycle {num} complete ({tc} tool calls)</ansigreen>"
                ))
            )
        except Exception as e:
            print_formatted_text(HTML(f"<b><ansired>Loop crashed: {escape(str(e))}</ansired></b>"))
            import traceback
            traceback.print_exc()

    def tail_logs(self):
        try:
            with open(self.cycles_log, "r") as f:
                f.seek(0, 2)
                while not self.pause_requested:
                    line = f.readline()
                    if line:
                        print_formatted_text(HTML(f"<style fg=\"#8a8a8a\">[LOG] {escape(line.strip())}</style>"))
                    else:
                        time.sleep(0.5)
        except Exception:
            pass

    def run(self):
        # 1. Print the Cool ASCII Banner using Rich (since it's before patch_stdout)
        console = Console()
        logo = '''
██████╗  ██████╗ ██████╗  ██████╗ ███████╗
██╔══██╗██╔═══██╗██╔══██╗██╔═══██╗██╔════╝
██████╔╝██║   ██║██████╔╝██║   ██║███████╗
██╔══██╗██║   ██║██╔══██╗██║   ██║╚════██║
██████╔╝╚██████╔╝██║  ██║╚██████╔╝███████║
╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
        '''
        text = Text(logo.strip("\n"), style="bold cyan")
        text.append("\n\nSelf-Evolving Agent", style="italic bright_black")
        panel = Panel(Align.center(text), border_style="cyan", padding=(1, 2))
        console.print(panel)
        console.print("")

        # 2. Boot health checks
        print_formatted_text(HTML("<b><ansigreen>Running Kernel Boot Sequence...</ansigreen></b>"))
        for skill in self.kernel.manifest.get("boot_sequence", []):
            print_formatted_text(HTML(f"<ansigreen>✔ {escape(skill)}</ansigreen>"))
            time.sleep(0.02)

        print_formatted_text(HTML(f"<ansigreen>✔ {len(self.kernel.registry)} functions loaded into registry</ansigreen>"))

        if self.kernel.evolution_llm:
            print_formatted_text(HTML(f"<ansigreen>✔ Evolution LLM: {self.kernel.config['providers']['evolution_api']['provider']}</ansigreen>"))
            try:
                print_formatted_text(HTML("<style fg=\"#8a8a8a\">  Testing Evolution LLM reachability...</style>"))
                self.kernel.evolution_llm.complete([{"role": "user", "content": "ping"}], system="Reply 'pong'")
                print_formatted_text(HTML("<ansigreen>  ✔ Evolution LLM is reachable</ansigreen>"))
            except Exception as e:
                print_formatted_text(HTML(f"<b><ansired>  ✗ Evolution LLM Unreachable: {escape(str(e))}</ansired></b>"))
        else:
            print_formatted_text(HTML("<ansiyellow>⚠ Evolution LLM not loaded (API key missing)</ansiyellow>"))

        if self.kernel.meta_eval_llm:
            print_formatted_text(HTML(f"<ansigreen>✔ Meta-Eval LLM: {self.kernel.config['providers']['meta_eval_api']['provider']}</ansigreen>"))
            try:
                print_formatted_text(HTML("<style fg=\"#8a8a8a\">  Testing Meta-Eval LLM reachability...</style>"))
                self.kernel.meta_eval_llm.complete([{"role": "user", "content": "ping"}], system="Reply 'pong'")
                print_formatted_text(HTML("<ansigreen>  ✔ Meta-Eval LLM is reachable</ansigreen>"))
            except Exception as e:
                print_formatted_text(HTML(f"<b><ansired>  ✗ Meta-Eval LLM Unreachable: {escape(str(e))}</ansired></b>"))
        else:
            print_formatted_text(HTML("<ansiyellow>⚠ Meta-Eval LLM not loaded (API key missing)</ansiyellow>"))

        # Director CLI
        session = PromptSession()

        # Boot mode selection
        print_formatted_text(HTML("\n<b><ansiblue>Select Boot Mode:</ansiblue></b>"))
        print_formatted_text(HTML(" 1. <ansimagenta>Evolution Mode</ansimagenta> (Autonomous self-improvement)"))
        print_formatted_text(HTML(" 2. <ansicyan>Digital Employee Mode</ansicyan> (Execution on demand)"))

        selected_mode = "evolution"
        while True:
            try:
                choice = session.prompt("Select [1/2]: ").strip()
                if choice == "1":
                    selected_mode = "evolution"
                    print_formatted_text(HTML("<b><ansimagenta>Starting in Evolution Mode...</ansimagenta></b>\n"))
                    break
                elif choice == "2":
                    selected_mode = "employee"
                    print_formatted_text(HTML("<b><ansicyan>Starting in Digital Employee Mode...</ansicyan></b>\n"))
                    break
                else:
                    print_formatted_text(HTML("<ansiyellow>Invalid choice. Please enter 1 or 2.</ansiyellow>"))
            except (KeyboardInterrupt, EOFError):
                return

        state_file = self.boros_root / "session" / "loop_state.json"
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
                state["mode"] = selected_mode
                state_file.write_text(json.dumps(state, indent=2))
            except Exception: pass

        # Start agent loop in background
        kernel_thread = threading.Thread(target=self.run_kernel_loop, daemon=True)
        kernel_thread.start()

        print_formatted_text(HTML("<b><ansiblue>Boros Director Interface</ansiblue></b>"))
        print_formatted_text(HTML("Commands: 'boros status', 'boros pause', 'boros resume', 'boros evolution', 'boros employee', or Ctrl+C to stop."))

        while True:
            try:
                with patch_stdout():
                    text = session.prompt("director> ")
                self.handle_command(text)
            except KeyboardInterrupt:
                print_formatted_text(HTML("<ansiyellow>Shutting down...</ansiyellow>"))
                self.pause_requested = True
                break
            except EOFError:
                self.pause_requested = True
                break

    def handle_command(self, text):
        text = text.strip()
        if not text:
            return
        if not text.startswith("boros "):
            print_formatted_text(HTML("<b><ansired>Commands must start with 'boros '</ansired></b>"))
            return

        cmd = text[6:].strip()
        if cmd == "status":
            state_file = self.boros_root / "session" / "loop_state.json"
            if state_file.exists():
                state = json.loads(state_file.read_text())
                print_formatted_text(HTML(f"<b><ansigreen>Loop State:</ansigreen></b> {escape(json.dumps(state, indent=2))}"))
            else:
                print_formatted_text(HTML("<ansiyellow>No active loop state.</ansiyellow>"))
            print_formatted_text(HTML(f"<b>Paused:</b> {self.pause_requested}"))
            print_formatted_text(HTML(f"<b>Registry:</b> {len(self.kernel.registry)} functions"))
        elif cmd == "pause":
            self.pause_requested = True
            print_formatted_text(HTML("<ansiyellow>Pause requested. Will stop at next cycle boundary.</ansiyellow>"))
        elif cmd == "resume":
            if self.pause_requested:
                self.pause_requested = False
                kernel_thread = threading.Thread(target=self.run_kernel_loop, daemon=True)
                kernel_thread.start()
                print_formatted_text(HTML("<ansigreen>Resumed evolution loop.</ansigreen>"))
        elif cmd == "evolution" or cmd == "employee":
            state_file = self.boros_root / "session" / "loop_state.json"
            if state_file.exists():
                state = json.loads(state_file.read_text())
                state["mode"] = cmd
                state_file.write_text(json.dumps(state, indent=2))
                if cmd == "evolution":
                    print_formatted_text(HTML("<b><ansimagenta>🔄 Switching to Evolution Mode</ansimagenta></b>"))
                else:
                    print_formatted_text(HTML("<b><ansicyan>🧑‍💻 Switching to Digital Employee Mode</ansicyan></b>"))
            else:
                print_formatted_text(HTML("<ansiyellow>Loop state file missing; cannot change mode yet.</ansiyellow>"))
        else:
            with open(self.pending_file, "r") as f:
                data = json.load(f)
            data["pending"].append(cmd)
            with open(self.pending_file, "w") as f:
                json.dump(data, f, indent=2)
            print_formatted_text(HTML(f"<ansiblue>Queued:</ansiblue> {escape(cmd)}"))
