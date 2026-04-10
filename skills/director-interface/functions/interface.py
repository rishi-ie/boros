import threading
import time
import json
import os
import re
import datetime
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

        self._adapt_thread = None

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

        if msg.startswith("[STATUS]"):
            text = escape(msg[8:].strip())
            print_formatted_text(HTML(f"<b><ansiwhite>▸ {text}</ansiwhite></b>"))
        elif msg.startswith("[CYCLE]"):
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
        _in_fork_state = False
        _boot_state_file = self.boros_root / "session" / "loop_state.json"
        if _boot_state_file.exists():
            try:
                _boot_state = json.loads(_boot_state_file.read_text())
                if _boot_state.get("agent_state") == "boros-fork":
                    _in_fork_state = True
                    selected_mode = "employee"
                    _gen = _boot_state.get("generation", 0)
                    _cycle = _boot_state.get("forked_at_cycle", "?")
                    print_formatted_text(HTML(
                        f"<b><ansimagenta>🔱 Resuming Boros-Fork  "
                        f"(Gen {_gen} — forked at cycle {_cycle})</ansimagenta></b>"
                    ))
                    print_formatted_text(HTML("<ansicyan>Deployment mode active — awaiting tasks.</ansicyan>\n"))
            except Exception:
                pass

        if not _in_fork_state:
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

        # Start adapt scheduler if resuming fork state
        if _in_fork_state:
            self._start_adapt_scheduler()

        # Start agent loop in background
        kernel_thread = threading.Thread(target=self.run_kernel_loop, daemon=True)
        kernel_thread.start()

        print_formatted_text(HTML("<b><ansiblue>Boros Director Interface</ansiblue></b>"))
        print_formatted_text(HTML(
            "Commands: <b>boros status</b> | <b>boros pause</b> | <b>boros resume</b> | "
            "<b>boros evolution</b> | <b>boros employee</b> | "
            "<b>boros fork</b> | <b>boros re-evolve</b> | "
            "<b>boros adapt</b> | <b>boros adapt-config &lt;interval&gt;</b> (e.g. 2d, 1w, 12h, off) "
            "| Ctrl+C to stop."
        ))

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
        elif cmd == "fork":
            self._handle_fork()
        elif cmd == "re-evolve":
            self._handle_re_evolve()
        elif cmd == "adapt":
            self._handle_adapt_now()
        elif cmd.startswith("adapt-config "):
            self._handle_adapt_config(cmd[len("adapt-config "):].strip())
        else:
            with open(self.pending_file, "r") as f:
                data = json.load(f)
            data["pending"].append(cmd)
            with open(self.pending_file, "w") as f:
                json.dump(data, f, indent=2)
            print_formatted_text(HTML(f"<ansiblue>Queued:</ansiblue> {escape(cmd)}"))

    # ─────────────────────────────────────────────
    # Fork / Re-Evolve / Adapt handlers
    # ─────────────────────────────────────────────

    def _handle_fork(self):
        state_file = self.boros_root / "session" / "loop_state.json"
        if not state_file.exists():
            print_formatted_text(HTML("<ansiyellow>No loop state found. Start a session first.</ansiyellow>"))
            return

        state = json.loads(state_file.read_text())
        if state.get("agent_state") == "boros-fork":
            print_formatted_text(HTML(
                "<ansiyellow>Already in boros-fork state. "
                "Use 'boros re-evolve' to start next generation evolution.</ansiyellow>"
            ))
            return

        # High-water marks become the fork's capability snapshot
        hw_file = self.boros_root / "skills" / "eval-bridge" / "state" / "high_water_marks.json"
        high_water = {}
        if hw_file.exists():
            try:
                high_water = json.loads(hw_file.read_text())
            except Exception:
                pass

        # Load or create lineage.json
        lineage_file = self.boros_root / "lineage.json"
        lineage = {"entries": []}
        if lineage_file.exists():
            try:
                lineage = json.loads(lineage_file.read_text())
            except Exception:
                pass

        generation = sum(1 for e in lineage.get("entries", []) if e.get("event") == "fork")

        config = json.loads((self.boros_root / "config.json").read_text())
        adaptation_interval = config.get("fork", {}).get("adaptation_interval", "2d")

        # Append fork node to lineage
        lineage["entries"].append({
            "event": "fork",
            "generation": generation,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "cycle_at_fork": state.get("cycle", 0),
            "total_cycles_completed": state.get("total_cycles_completed", 0),
            "agent_state": "boros-fork",
            "high_water_marks": high_water,
            "adaptation_interval": adaptation_interval
        })
        lineage_file.write_text(json.dumps(lineage, indent=2))

        # Lock the mode
        state["mode"] = "employee"
        state["agent_state"] = "boros-fork"
        state["forked_at_cycle"] = state.get("cycle", 0)
        state["generation"] = generation
        state_file.write_text(json.dumps(state, indent=2))

        self._start_adapt_scheduler()

        print_formatted_text(HTML(f"<b><ansimagenta>🔱 BOROS FORKED — Generation {generation}</ansimagenta></b>"))
        print_formatted_text(HTML(f"<ansigreen>Forked at cycle {state['forked_at_cycle']}</ansigreen>"))
        print_formatted_text(HTML(f"<ansicyan>Capability snapshot: {escape(json.dumps(high_water))}</ansicyan>"))
        print_formatted_text(HTML(f"<ansiyellow>Adaptation scheduled every: {adaptation_interval}</ansiyellow>"))
        print_formatted_text(HTML(
            "<style fg='#8a8a8a'>Running as a pure work agent. "
            "Use 'boros re-evolve' to begin next generation.</style>"
        ))

    def _handle_re_evolve(self):
        state_file = self.boros_root / "session" / "loop_state.json"
        if not state_file.exists():
            print_formatted_text(HTML("<ansiyellow>No loop state found.</ansiyellow>"))
            return

        state = json.loads(state_file.read_text())

        lineage_file = self.boros_root / "lineage.json"
        lineage = {"entries": []}
        if lineage_file.exists():
            try:
                lineage = json.loads(lineage_file.read_text())
            except Exception:
                pass

        generation = sum(1 for e in lineage.get("entries", []) if e.get("event") == "fork")

        # Read task log to seed the first REFLECT cycle
        task_log_file = self.boros_root / "logs" / "task_log.jsonl"
        recent_tasks = []
        if task_log_file.exists():
            try:
                lines = [l for l in task_log_file.read_text(encoding="utf-8").strip().split("\n") if l.strip()]
                recent_tasks = [json.loads(l) for l in lines[-50:]]
            except Exception:
                pass

        adapt_seed = {
            "source": "boros-fork field deployment data",
            "generation": generation,
            "task_count": len(recent_tasks),
            "recent_tasks": recent_tasks[-10:],
            "instruction": (
                f"You are beginning evolution generation {generation}. "
                "The tasks above are real requests users gave you during deployment. "
                "Identify capability gaps — tasks that failed, had high retries, or had no skill to handle them. "
                "Your first evolution targets should address these real-world gaps."
            )
        }
        (self.boros_root / "session" / "adapt_seed.json").write_text(
            json.dumps(adapt_seed, indent=2)
        )

        lineage["entries"].append({
            "event": "re-evolve",
            "generation": generation,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "tasks_since_fork": len(recent_tasks),
            "world_model": "world_model.json"
        })
        lineage_file.write_text(json.dumps(lineage, indent=2))

        state["mode"] = "evolution"
        state["agent_state"] = "evolution"
        state["generation"] = generation
        state.pop("forked_at_cycle", None)
        state_file.write_text(json.dumps(state, indent=2))

        self.pause_requested = False
        kernel_thread = threading.Thread(target=self.run_kernel_loop, daemon=True)
        kernel_thread.start()

        print_formatted_text(HTML(f"<b><ansimagenta>🔄 Re-Evolution Started — Generation {generation}</ansimagenta></b>"))
        print_formatted_text(HTML(f"<ansicyan>Seeded with {len(recent_tasks)} tasks from field deployment.</ansicyan>"))
        print_formatted_text(HTML(
            "<ansigreen>Evolution loop restarted. "
            "Edit world_model.json before running to target new capabilities.</ansigreen>"
        ))

    def _handle_adapt_now(self):
        state_file = self.boros_root / "session" / "loop_state.json"
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
                if state.get("agent_state") != "boros-fork":
                    print_formatted_text(HTML(
                        "<ansiyellow>Adapt is only available in boros-fork state. "
                        "Run 'boros fork' first.</ansiyellow>"
                    ))
                    return
            except Exception:
                pass

        print_formatted_text(HTML("<ansicyan>Running adaptation cycle...</ansicyan>"))
        threading.Thread(target=self._run_adapt_engine, daemon=True).start()

    def _handle_adapt_config(self, interval):
        valid_units = ("h", "d", "w", "m")
        if interval != "off" and not (len(interval) >= 2 and interval[-1] in valid_units and interval[:-1].isdigit()):
            print_formatted_text(HTML(
                f"<ansired>Invalid interval '{escape(interval)}'. "
                "Use format: 2d, 1w, 12h, 30m, or 'off'</ansired>"
            ))
            return

        config_path = self.boros_root / "config.json"
        try:
            config = json.loads(config_path.read_text())
            if "fork" not in config:
                config["fork"] = {}
            config["fork"]["adaptation_interval"] = interval
            config_path.write_text(json.dumps(config, indent=2))
            print_formatted_text(HTML(f"<ansigreen>Adaptation interval set to: {escape(interval)}</ansigreen>"))
            if interval != "off":
                self._start_adapt_scheduler()
        except Exception as e:
            print_formatted_text(HTML(f"<ansired>Failed to update config: {escape(str(e))}</ansired>"))

    def _run_adapt_engine(self):
        try:
            import sys
            sys.path.insert(0, str(self.boros_root.parent))
            from boros.adapt_engine import AdaptEngine
            engine = AdaptEngine(self.kernel, log_callback=self.log_to_console)
            result = engine.run()
            if result:
                print_formatted_text(HTML("<ansigreen>✔ Adaptation complete — changes applied.</ansigreen>"))
            else:
                print_formatted_text(HTML("<ansiyellow>Adaptation cycle complete — no changes applied.</ansiyellow>"))
        except Exception as e:
            print_formatted_text(HTML(f"<ansired>Adaptation engine error: {escape(str(e))}</ansired>"))

    def _start_adapt_scheduler(self):
        if self._adapt_thread and self._adapt_thread.is_alive():
            return
        self._adapt_thread = threading.Thread(target=self._adapt_scheduler_loop, daemon=True)
        self._adapt_thread.start()

    def _adapt_scheduler_loop(self):
        """Background thread: fires adapt engine when the configured interval has elapsed."""
        while not self.pause_requested:
            try:
                config_path = self.boros_root / "config.json"
                config = json.loads(config_path.read_text())
                fork_cfg = config.get("fork", {})
                interval_str = fork_cfg.get("adaptation_interval", "off")

                if interval_str == "off":
                    time.sleep(60)
                    continue

                interval_seconds = self._parse_interval_seconds(interval_str)
                if interval_seconds is None:
                    time.sleep(60)
                    continue

                last_ts = fork_cfg.get("last_adapt_timestamp")
                if last_ts:
                    last_dt = datetime.datetime.fromisoformat(last_ts.rstrip("Z"))
                    elapsed = (datetime.datetime.utcnow() - last_dt).total_seconds()
                    if elapsed < interval_seconds:
                        time.sleep(60)
                        continue

                # Only fire when still in fork state
                state_file = self.boros_root / "session" / "loop_state.json"
                if state_file.exists():
                    state = json.loads(state_file.read_text())
                    if state.get("agent_state") != "boros-fork":
                        time.sleep(60)
                        continue

                self.log_to_console("[ADAPT] Scheduled adaptation triggered.")
                self._run_adapt_engine()

            except Exception:
                pass

            time.sleep(60)

    def _parse_interval_seconds(self, interval_str):
        if not interval_str or interval_str == "off":
            return None
        try:
            unit = interval_str[-1]
            value = int(interval_str[:-1])
            return value * {"m": 60, "h": 3600, "d": 86400, "w": 604800}.get(unit, 0) or None
        except Exception:
            return None
