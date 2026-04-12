import threading
import time
import json
import re
import datetime
import sys
from pathlib import Path
from prompt_toolkit import PromptSession, print_formatted_text, HTML
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from rich.table import Table
from rich.panel import Panel


def escape(t):
    return str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


class DirectorInterface:
    def __init__(self, kernel):
        self.kernel       = kernel
        self.boros_root   = kernel.boros_root
        self.pause_requested = False
        self.verbose      = False
        self._adapt_thread = None
        self._console     = Console()

        # Ensure runtime dirs exist
        self.commands_dir = self.boros_root / "commands"
        self.commands_dir.mkdir(parents=True, exist_ok=True)
        self.pending_file = self.commands_dir / "pending.json"
        if not self.pending_file.exists():
            self.pending_file.write_text(json.dumps({"pending": []}))

        self.logs_dir  = self.boros_root / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.cycles_log = self.logs_dir / "cycles.log"
        if not self.cycles_log.exists():
            self.cycles_log.touch()

    # ─────────────────────────────────────────────
    # Log output
    # ─────────────────────────────────────────────

    def log_to_console(self, msg):
        # Always persist to file
        try:
            with open(self.cycles_log, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

        if not msg:
            return

        # Quiet mode: suppress raw tool I/O and token counts
        if not self.verbose:
            if msg.startswith("[TOOL]") or msg.startswith("[EXEC TOOL]") or msg.startswith("[TOKENS]"):
                return

        # Strip ANSI escape codes
        msg = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', str(msg)).strip()
        if not msg:
            return

        def _fmt_result(text, max_len=150):
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    if data.get("status") == "error" or ("returncode" in data and data.get("returncode", 0) != 0):
                        err = data.get("error", data.get("stderr", "error"))
                        return f"<b><ansired>Error:</ansired></b> {escape(str(err).strip()[:max_len])}", True
                    out = data.get("stdout", data.get("output", data.get("result", "")))
                    if isinstance(out, (dict, list)):
                        out = json.dumps(out)
                    if not out and data.get("status") == "ok":
                        out = "ok"
                    return escape(str(out).strip()[:max_len].replace("\n", " ")), False
            except Exception:
                pass
            t = text.replace('\n', ' ')
            return escape(t[:max_len] + ("..." if len(t) > max_len else "")), False

        if msg.startswith("[STATUS]"):
            print_formatted_text(HTML(f"<b><ansiwhite>▸ {escape(msg[8:].strip())}</ansiwhite></b>"))

        elif msg.startswith("[CYCLE]"):
            print_formatted_text(HTML(f"\n<b><ansimagenta>🔄 {escape(msg[7:].strip())}</ansimagenta></b>"))

        elif msg.startswith("[ERROR]"):
            print_formatted_text(HTML(f"<b><ansired>✗ {escape(msg[7:].strip())}</ansired></b>"))

        elif msg.startswith("[BOROS]"):
            print_formatted_text(HTML(
                f"<ansicyan>🧠 Boros:</ansicyan> <b><ansiwhite>{escape(msg[7:].strip())}</ansiwhite></b>"
            ))

        elif msg.startswith("[BOROS EXECUTION]"):
            print_formatted_text(HTML(
                f"<ansicyan>🚀 Executing:</ansicyan> <b><ansiwhite>{escape(msg[17:].strip())}</ansiwhite></b>"
            ))

        elif msg.startswith("[TOKENS]"):
            print_formatted_text(HTML(f"<style fg='ansiwhite'>📊 {escape(msg[8:].strip())}</style>"))

        elif msg.startswith("[TOOL] →"):
            print_formatted_text(HTML(
                f"<ansiyellow>⚡ Tool:</ansiyellow> <style fg='#8a8a8a'>{escape(msg[8:].strip())}</style>"
            ))

        elif msg.startswith("[TOOL] ←"):
            preview, is_error = _fmt_result(msg[8:].strip())
            if is_error:
                print_formatted_text(HTML(f"<b><ansired>✗ Tool Failed:</ansired></b> <style fg='#ff8787'>{preview}</style>"))
            else:
                print_formatted_text(HTML(f"<b><ansigreen>✔ Tool:</ansigreen></b> <style fg='#87ff87'>{preview}</style>"))

        elif msg.startswith("[EXEC TOOL] →"):
            print_formatted_text(HTML(
                f"<ansiyellow>⚡ Tool:</ansiyellow> <style fg='#8a8a8a'>{escape(msg[13:].strip())}</style>"
            ))

        elif msg.startswith("[EXEC TOOL] ←"):
            preview, is_error = _fmt_result(msg[13:].strip())
            if is_error:
                print_formatted_text(HTML(f"<b><ansired>✗ Tool Failed:</ansired></b> <style fg='#ff8787'>{preview}</style>"))
            else:
                print_formatted_text(HTML(f"<b><ansigreen>✔ Tool:</ansigreen></b> <style fg='#87ff87'>{preview}</style>"))

        elif "📝 [PROPOSAL CREATED]" in msg:
            print_formatted_text(HTML("<b><ansicyan> 📝 PROPOSAL CREATED </ansicyan></b>"))

        elif "⚙️ [CODE MUTATION]" in msg:
            print_formatted_text(HTML("<b><ansiyellow> ⚙️  CODE MUTATED </ansiyellow></b>"))

        elif msg.startswith("[+]"):
            print_formatted_text(HTML(f"<ansigreen>{escape(msg[:150])}</ansigreen>"))

        elif msg.startswith("[-]"):
            print_formatted_text(HTML(f"<ansired>{escape(msg[:150])}</ansired>"))

        elif msg.startswith("[RATE_LIMIT]"):
            print_formatted_text(HTML(f"<b><ansiyellow>⏳ {escape(msg)}</ansiyellow></b>"))

        elif msg.startswith("[LOOP]"):
            print_formatted_text(HTML(f"<style fg='#8a8a8a'>{escape(msg[6:].strip())}</style>"))

        elif msg.startswith("[ADAPT]"):
            print_formatted_text(HTML(
                f"<ansicyan>⚙  Adapt:</ansicyan> <style fg='ansiwhite'>{escape(msg[7:].strip())}</style>"
            ))

        elif msg.startswith("---") or msg.startswith("====="):
            pass  # decorative separators — suppress

        else:
            if "Command failed with return code" in msg:
                print_formatted_text(HTML(f"<ansired>{escape(msg.strip())}</ansired>"))
            else:
                out = msg.strip().replace('\n', ' ')
                if len(out) > 150:
                    out = out[:147] + "..."
                print_formatted_text(HTML(f"<style fg='#8a8a8a'>{escape(out)}</style>"))

    # ─────────────────────────────────────────────
    # Kernel loop (background thread)
    # ─────────────────────────────────────────────

    def run_kernel_loop(self):
        if self.kernel.evolution_llm is None:
            print_formatted_text(HTML(
                "<b><ansired>Cannot start — no LLM loaded. Check API key and restart.</ansired></b>"
            ))
            return

        from agent_loop import AgentLoop
        loop = AgentLoop(self.kernel, log_callback=self.log_to_console)
        try:
            loop.run_continuous(
                should_pause=lambda: self.pause_requested,
                on_cycle_complete=lambda num, tc: print_formatted_text(HTML(
                    f"<ansigreen>✔ Cycle {num} done  ({tc} tool calls)</ansigreen>"
                ))
            )
        except Exception as e:
            import traceback
            print_formatted_text(HTML(f"<b><ansired>Loop crashed: {escape(str(e))}</ansired></b>"))
            traceback.print_exc()

    # ─────────────────────────────────────────────
    # Main entry point
    # ─────────────────────────────────────────────

    def run(self):
        session    = PromptSession()
        state_file = self.boros_root / "session" / "loop_state.json"

        selected_mode  = "evolution"
        _in_fork_state = False

        # Read persisted state
        state = {}
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
            except Exception:
                pass

        total_cycles = state.get("total_cycles_completed", 0)
        current_cycle = state.get("cycle", 0)
        is_first_boot = (total_cycles == 0 and current_cycle == 0)

        if is_first_boot:
            # Only time mode selection prompt appears
            print_formatted_text(HTML("\n<b>Select a mode to start:</b>"))
            print_formatted_text(HTML("  <b>1</b>  <ansimagenta>evolve</ansimagenta>  — autonomous self-improvement"))
            print_formatted_text(HTML("  <b>2</b>  <ansicyan>work</ansicyan>    — on-demand task execution\n"))
            while True:
                try:
                    choice = session.prompt("  → ").strip()
                    if choice == "1":
                        selected_mode = "evolution"
                        break
                    elif choice == "2":
                        selected_mode = "employee"
                        break
                    else:
                        print_formatted_text(HTML("<ansiyellow>Enter 1 or 2.</ansiyellow>"))
                except (KeyboardInterrupt, EOFError):
                    sys.exit(0)
        else:
            agent_state   = state.get("agent_state", "")
            selected_mode = state.get("mode", "evolution")

            if agent_state == "boros-fork":
                _in_fork_state = True
                selected_mode  = "employee"
                gen   = state.get("generation", 0)
                cycle = state.get("forked_at_cycle", "?")
                print_formatted_text(HTML(
                    f"<b><ansimagenta>🔱 Boros-Fork  Gen {gen}  ·  forked at cycle {cycle}</ansimagenta></b>"
                ))
            elif selected_mode == "evolution":
                print_formatted_text(HTML(
                    f"<ansimagenta>Resuming Evolution  ·  Cycle {current_cycle}</ansimagenta>"
                ))
            else:
                print_formatted_text(HTML("<ansicyan>Resuming Work Mode</ansicyan>"))

        # Persist selected mode
        if state_file.exists():
            try:
                state["mode"] = selected_mode
                state_file.write_text(json.dumps(state, indent=2))
            except Exception:
                pass

        if _in_fork_state:
            self._start_adapt_scheduler()

        threading.Thread(target=self.run_kernel_loop, daemon=True).start()
        print_formatted_text(HTML(""))

        # ── Command loop ──────────────────────────────
        while True:
            try:
                with patch_stdout():
                    text = session.prompt("boros> ").strip()
                if text:
                    self.handle_command(text)
            except KeyboardInterrupt:
                self._do_quit()
            except EOFError:
                self._do_quit()

    # ─────────────────────────────────────────────
    # Command dispatch
    # ─────────────────────────────────────────────

    def handle_command(self, raw):
        parts = raw.strip().split()
        if not parts:
            return
        cmd = parts[0].lower()

        if cmd == "status":
            self._cmd_status()
        elif cmd == "pause":
            self._cmd_pause()
        elif cmd == "resume":
            self._cmd_resume()
        elif cmd == "stop":
            self._cmd_stop()
        elif cmd in ("evolve", "evolution"):
            self._cmd_set_mode("evolution")
        elif cmd in ("work", "employee"):
            self._cmd_set_mode("employee")
        elif cmd == "fork":
            self._handle_fork()
        elif cmd == "re-evolve":
            self._handle_re_evolve()
        elif cmd == "adapt":
            # "adapt" or "adapt config 2d"
            if len(parts) >= 2 and parts[1] == "config":
                self._handle_adapt_config(parts[2] if len(parts) >= 3 else "")
            else:
                self._handle_adapt_now()
        elif cmd == "adapt-config":
            self._handle_adapt_config(parts[1] if len(parts) >= 2 else "")
        elif cmd == "verbose":
            self.verbose = True
            print_formatted_text(HTML("<ansigreen>Verbose on — full tool trace visible.</ansigreen>"))
        elif cmd == "quiet":
            self.verbose = False
            print_formatted_text(HTML("<ansigreen>Quiet mode — summary output only.</ansigreen>"))
        elif cmd == "logs":
            n = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else 20
            self._cmd_logs(n)
        elif cmd in ("help", "?"):
            self._cmd_help()
        elif cmd in ("quit", "exit"):
            self._do_quit()
        else:
            print_formatted_text(HTML(
                f"<ansiyellow>Unknown command: <b>{escape(raw)}</b>  —  "
                f"type <b>help</b> to see available commands.</ansiyellow>"
            ))

    # ─────────────────────────────────────────────
    # Command implementations
    # ─────────────────────────────────────────────

    def _cmd_status(self):
        state_file   = self.boros_root / "session" / "loop_state.json"
        hw_file      = self.boros_root / "skills" / "eval-bridge" / "state" / "high_water_marks.json"
        lineage_file = self.boros_root / "lineage.json"

        state       = {}
        high_water  = {}

        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
            except Exception:
                pass
        if hw_file.exists():
            try:
                high_water = json.loads(hw_file.read_text())
            except Exception:
                pass

        mode       = state.get("agent_state", state.get("mode", "evolution"))
        cycle      = state.get("cycle", 0)
        stage      = state.get("stage") or "—"
        generation = state.get("generation", 0)
        paused     = "yes" if self.pause_requested else "no"

        snapshots  = 0
        snap_dir   = self.boros_root / "snapshots"
        if snap_dir.exists():
            snapshots = len(list(snap_dir.glob("snap-*")))

        skill_count    = len(self.kernel.manifest.get("skills", {}))
        registry_count = len(self.kernel.registry)

        table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
        table.add_column(style="dim", no_wrap=True)
        table.add_column()

        mode_style = "magenta" if "evol" in mode else "cyan"
        table.add_row("Mode",   f"[{mode_style}]{mode}[/{mode_style}]  ·  paused: {paused}")
        table.add_row("Cycle",  f"{cycle}  ·  {stage}")
        table.add_row("Gen",    f"{generation}  ·  snapshots: {snapshots}")

        if high_water:
            table.add_row("", "")
            for cat, score in high_water.items():
                if isinstance(score, (int, float)):
                    filled = int(score * 10)
                    bar    = "█" * filled + "░" * (10 - filled)
                    pct    = int(score * 100)
                    best   = "  [green]best[/green]" if score > 0 else ""
                    table.add_row(cat, f"{score:.3f}  [green]{bar}[/green]  {pct}%{best}")

        table.add_row("", "")
        table.add_row("Skills", f"{skill_count} loaded  ·  {registry_count} functions")

        self._console.print()
        self._console.print(Panel(table, title="[bold]Boros[/bold]", border_style="cyan", padding=(0, 1)))
        self._console.print()

    def _cmd_pause(self):
        self.pause_requested = True
        print_formatted_text(HTML("<ansiyellow>Pausing — will stop at end of current cycle.</ansiyellow>"))

    def _cmd_resume(self):
        if not self.pause_requested:
            print_formatted_text(HTML("<ansiyellow>Not paused.</ansiyellow>"))
            return
        self.pause_requested = False
        threading.Thread(target=self.run_kernel_loop, daemon=True).start()
        print_formatted_text(HTML("<ansigreen>Resumed.</ansigreen>"))

    def _cmd_stop(self):
        self.pause_requested = True
        print_formatted_text(HTML("<ansiyellow>Stopping.</ansiyellow>"))
        sys.exit(0)

    def _cmd_set_mode(self, mode):
        state_file = self.boros_root / "session" / "loop_state.json"
        if not state_file.exists():
            print_formatted_text(HTML("<ansiyellow>No active session.</ansiyellow>"))
            return
        try:
            state = json.loads(state_file.read_text())
            state["mode"] = mode
            # Clear fork lock when explicitly switching modes
            if state.get("agent_state") == "boros-fork" and mode in ("evolution", "employee"):
                state["agent_state"] = mode
            state_file.write_text(json.dumps(state, indent=2))
            if mode == "evolution":
                print_formatted_text(HTML("<b><ansimagenta>Switched to Evolution Mode.</ansimagenta></b>"))
            else:
                print_formatted_text(HTML("<b><ansicyan>Switched to Work Mode.</ansicyan></b>"))
        except Exception as e:
            print_formatted_text(HTML(f"<ansired>Failed: {escape(str(e))}</ansired>"))

    def _cmd_logs(self, n):
        candidates = [
            self.boros_root / "logs" / "cycles.log",
            self.boros_root / "logs" / "execution_cycles.log",
        ]
        existing = [f for f in candidates if f.exists() and f.stat().st_size > 0]
        if not existing:
            print_formatted_text(HTML("<ansiyellow>No logs yet.</ansiyellow>"))
            return
        log_file = max(existing, key=lambda f: f.stat().st_mtime)
        try:
            lines  = log_file.read_text(encoding="utf-8", errors="replace").strip().split("\n")
            recent = [l for l in lines if l.strip()][-n:]
            print_formatted_text(HTML(
                f"<style fg='#8a8a8a'>── {log_file.name}  (last {len(recent)} lines) ──</style>"
            ))
            for line in recent:
                print_formatted_text(HTML(f"<style fg='#8a8a8a'>{escape(line)}</style>"))
        except Exception as e:
            print_formatted_text(HTML(f"<ansired>Could not read logs: {escape(str(e))}</ansired>"))

    def _cmd_help(self):
        table = Table(show_header=False, box=None, padding=(0, 3, 0, 0))
        table.add_column(style="bold cyan", no_wrap=True, min_width=24)
        table.add_column(style="dim")

        rows = [
            ("status",             "Show current state and scores"),
            ("pause",              "Pause after current cycle completes"),
            ("resume",             "Resume from pause"),
            ("stop",               "Stop immediately"),
            ("",                   ""),
            ("evolve",             "Switch to evolution mode"),
            ("work",               "Switch to work mode  (accepts queued tasks)"),
            ("fork",               "Freeze evolved state as a deployment agent"),
            ("re-evolve",          "Start next-generation evolution from fork"),
            ("adapt",              "Run an adaptation cycle now"),
            ("adapt-config <t>",   "Set adaptation schedule  (2d, 1w, 12h, 30m, off)"),
            ("",                   ""),
            ("verbose",            "Show full tool trace output"),
            ("quiet",              "Show summary output only  (default)"),
            ("logs [n]",           "Show last n log lines  (default 20)"),
            ("",                   ""),
            ("help",               "Show this help"),
            ("quit  /  exit",      "Exit Boros"),
        ]
        for cmd, desc in rows:
            table.add_row(cmd, desc)

        self._console.print()
        self._console.print(table)
        self._console.print()

    def _do_quit(self):
        self.pause_requested = True
        sys.exit(0)

    # ─────────────────────────────────────────────
    # Fork / Re-Evolve / Adapt
    # ─────────────────────────────────────────────

    def _handle_fork(self):
        state_file = self.boros_root / "session" / "loop_state.json"
        if not state_file.exists():
            print_formatted_text(HTML("<ansiyellow>No active session.</ansiyellow>"))
            return

        state = json.loads(state_file.read_text())
        if state.get("agent_state") == "boros-fork":
            print_formatted_text(HTML(
                "<ansiyellow>Already forked. Use <b>re-evolve</b> to start next generation.</ansiyellow>"
            ))
            return

        hw_file    = self.boros_root / "skills" / "eval-bridge" / "state" / "high_water_marks.json"
        high_water = {}
        if hw_file.exists():
            try:
                high_water = json.loads(hw_file.read_text())
            except Exception:
                pass

        lineage_file = self.boros_root / "lineage.json"
        lineage      = {"entries": []}
        if lineage_file.exists():
            try:
                lineage = json.loads(lineage_file.read_text())
            except Exception:
                pass

        generation = sum(1 for e in lineage.get("entries", []) if e.get("event") == "fork")
        config     = json.loads((self.boros_root / "config.json").read_text())
        interval   = config.get("fork", {}).get("adaptation_interval", "2d")

        lineage["entries"].append({
            "event":                 "fork",
            "generation":            generation,
            "timestamp":             datetime.datetime.utcnow().isoformat() + "Z",
            "cycle_at_fork":         state.get("cycle", 0),
            "total_cycles_completed":state.get("total_cycles_completed", 0),
            "agent_state":           "boros-fork",
            "high_water_marks":      high_water,
            "adaptation_interval":   interval,
        })
        lineage_file.write_text(json.dumps(lineage, indent=2))

        state["mode"]           = "employee"
        state["agent_state"]    = "boros-fork"
        state["forked_at_cycle"]= state.get("cycle", 0)
        state["generation"]     = generation
        state_file.write_text(json.dumps(state, indent=2))

        self._start_adapt_scheduler()

        # Delegate to civilization skill for identity + genome + lineage
        child_id = None
        if "civ_fork_child" in self.kernel.registry:
            try:
                civ_result = self.kernel.registry["civ_fork_child"]({}, self.kernel)
                child_id = civ_result.get("child_id")
            except Exception as e:
                print_formatted_text(HTML(f"<ansiyellow>Civilization fork failed: {escape(str(e))}</ansiyellow>"))

        print_formatted_text(HTML(f"<b><ansimagenta>🔱 Forked — Generation {generation}</ansimagenta></b>"))
        if child_id:
            print_formatted_text(HTML(f"<ansicyan>Child ID: {escape(child_id)}</ansicyan>"))
        print_formatted_text(HTML(f"<ansigreen>Scores at fork: {escape(json.dumps(high_water))}</ansigreen>"))
        print_formatted_text(HTML(f"<ansiyellow>Adaptation every {interval}  ·  use <b>adapt-config</b> to change</ansiyellow>"))
        print_formatted_text(HTML(
            "<style fg='#8a8a8a'>Now a deployment agent. Type <b>re-evolve</b> to begin next generation.</style>"
        ))

    def _handle_re_evolve(self):
        state_file = self.boros_root / "session" / "loop_state.json"
        if not state_file.exists():
            print_formatted_text(HTML("<ansiyellow>No active session.</ansiyellow>"))
            return

        state = json.loads(state_file.read_text())

        lineage_file = self.boros_root / "lineage.json"
        lineage      = {"entries": []}
        if lineage_file.exists():
            try:
                lineage = json.loads(lineage_file.read_text())
            except Exception:
                pass

        generation = sum(1 for e in lineage.get("entries", []) if e.get("event") == "fork")

        # Seed first REFLECT with real deployment task history
        task_log_file = self.boros_root / "logs" / "task_log.jsonl"
        recent_tasks  = []
        if task_log_file.exists():
            try:
                lines        = [l for l in task_log_file.read_text(encoding="utf-8").strip().split("\n") if l.strip()]
                recent_tasks = [json.loads(l) for l in lines[-50:]]
            except Exception:
                pass

        (self.boros_root / "session" / "adapt_seed.json").write_text(json.dumps({
            "source":       "boros-fork field deployment data",
            "generation":   generation,
            "task_count":   len(recent_tasks),
            "recent_tasks": recent_tasks[-10:],
            "instruction":  (
                f"You are beginning evolution generation {generation}. "
                "Study the task history above — these are real requests from deployment. "
                "Identify capability gaps and target them in your first evolution cycles."
            ),
        }, indent=2))

        lineage["entries"].append({
            "event":           "re-evolve",
            "generation":      generation,
            "timestamp":       datetime.datetime.utcnow().isoformat() + "Z",
            "tasks_since_fork":len(recent_tasks),
            "world_model":     "world_model.json",
        })
        lineage_file.write_text(json.dumps(lineage, indent=2))

        state["mode"]       = "evolution"
        state["agent_state"]= "evolution"
        state["generation"] = generation
        state.pop("forked_at_cycle", None)
        state_file.write_text(json.dumps(state, indent=2))

        self.pause_requested = False
        threading.Thread(target=self.run_kernel_loop, daemon=True).start()

        print_formatted_text(HTML(f"<b><ansimagenta>🔄 Re-Evolution started — Generation {generation}</ansimagenta></b>"))
        print_formatted_text(HTML(f"<ansicyan>Seeded with {len(recent_tasks)} real deployment tasks.</ansicyan>"))
        print_formatted_text(HTML(
            "<ansigreen>Edit world_model.json to add new capability targets, then watch it evolve.</ansigreen>"
        ))

    def _handle_adapt_now(self):
        state_file = self.boros_root / "session" / "loop_state.json"
        if state_file.exists():
            try:
                if json.loads(state_file.read_text()).get("agent_state") != "boros-fork":
                    print_formatted_text(HTML(
                        "<ansiyellow>Adapt is only available after <b>fork</b>.</ansiyellow>"
                    ))
                    return
            except Exception:
                pass
        print_formatted_text(HTML("<ansicyan>Running adaptation cycle...</ansicyan>"))
        threading.Thread(target=self._run_adapt_engine, daemon=True).start()

    def _handle_adapt_config(self, interval):
        if not interval:
            print_formatted_text(HTML(
                "<ansiyellow>Usage: adapt-config &lt;interval&gt;  (2d, 1w, 12h, 30m, off)</ansiyellow>"
            ))
            return
        valid_units = ("h", "d", "w", "m")
        if interval != "off" and not (
            len(interval) >= 2 and interval[-1] in valid_units and interval[:-1].isdigit()
        ):
            print_formatted_text(HTML(
                f"<ansired>Invalid: '{escape(interval)}'. Use 2d, 1w, 12h, 30m, or off</ansired>"
            ))
            return
        try:
            config_path = self.boros_root / "config.json"
            config = json.loads(config_path.read_text())
            config.setdefault("fork", {})["adaptation_interval"] = interval
            config_path.write_text(json.dumps(config, indent=2))
            print_formatted_text(HTML(f"<ansigreen>Adaptation interval set to {escape(interval)}.</ansigreen>"))
            if interval != "off":
                self._start_adapt_scheduler()
        except Exception as e:
            print_formatted_text(HTML(f"<ansired>Failed: {escape(str(e))}</ansired>"))

    def _run_adapt_engine(self):
        try:
            sys.path.insert(0, str(self.boros_root.parent))
            from adapt_engine import AdaptEngine
            result = AdaptEngine(self.kernel, log_callback=self.log_to_console).run()
            if result:
                print_formatted_text(HTML("<ansigreen>✔ Adaptation complete — changes applied.</ansigreen>"))
            else:
                print_formatted_text(HTML("<ansiyellow>Adaptation complete — no changes applied.</ansiyellow>"))
        except Exception as e:
            print_formatted_text(HTML(f"<ansired>Adaptation error: {escape(str(e))}</ansired>"))

    def _start_adapt_scheduler(self):
        if self._adapt_thread and self._adapt_thread.is_alive():
            return
        self._adapt_thread = threading.Thread(target=self._adapt_scheduler_loop, daemon=True)
        self._adapt_thread.start()

    def _adapt_scheduler_loop(self):
        while not self.pause_requested:
            try:
                config   = json.loads((self.boros_root / "config.json").read_text())
                fork_cfg = config.get("fork", {})
                interval_str = fork_cfg.get("adaptation_interval", "off")

                if interval_str == "off":
                    time.sleep(60)
                    continue

                interval_sec = self._parse_interval_seconds(interval_str)
                if interval_sec is None:
                    time.sleep(60)
                    continue

                last_ts = fork_cfg.get("last_adapt_timestamp")
                if not last_ts:
                    # No prior adapt — initialize timestamp so interval starts from now
                    config["fork"]["last_adapt_timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
                    (self.boros_root / "config.json").write_text(json.dumps(config, indent=2))
                    time.sleep(60)
                    continue
                last_dt = datetime.datetime.fromisoformat(last_ts.rstrip("Z"))
                if (datetime.datetime.utcnow() - last_dt).total_seconds() < interval_sec:
                    time.sleep(60)
                    continue

                state_file = self.boros_root / "session" / "loop_state.json"
                if state_file.exists():
                    if json.loads(state_file.read_text()).get("agent_state") != "boros-fork":
                        time.sleep(60)
                        continue

                self.log_to_console("[ADAPT] Scheduled adaptation triggered.")
                self._run_adapt_engine()

            except Exception:
                pass

            time.sleep(60)

    def _parse_interval_seconds(self, s):
        if not s or s == "off":
            return None
        try:
            v = int(s[:-1])
            u = s[-1]
            return v * {"m": 60, "h": 3600, "d": 86400, "w": 604800}.get(u, 0) or None
        except Exception:
            return None
