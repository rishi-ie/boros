import threading
import time
import json
import os
from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console

console = Console()

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
        """Callback for agent loop to print to rich console."""
        console.print(f"[dim]{msg}[/dim]")
        # Also append to log file
        try:
            with open(self.cycles_log, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

    def run_kernel_loop(self):
        """Run the actual agentic evolution loop in background."""
        console.print("[bold green]Starting Boros evolution loop...[/bold green]")

        if self.kernel.evolution_llm is None:
            console.print("[bold red]Cannot start loop: No evolution LLM adapter loaded.[/red]")
            console.print("[yellow]Set ANTHROPIC_API_KEY in environment or boros/.env, then restart.[/yellow]")
            return

        from boros.agent_loop import AgentLoop
        loop = AgentLoop(self.kernel, log_callback=self.log_to_console)

        try:
            loop.run_continuous(
                should_pause=lambda: self.pause_requested,
                on_cycle_complete=lambda num, tc: console.print(
                    f"[green]✔ Cycle {num} complete ({tc} tool calls)[/green]"
                )
            )
        except Exception as e:
            console.print(f"[red]Loop crashed: {e}[/red]")
            import traceback
            traceback.print_exc()

    def tail_logs(self):
        try:
            with open(self.cycles_log, "r") as f:
                f.seek(0, 2)
                while not self.pause_requested:
                    line = f.readline()
                    if line:
                        console.print(f"[dim][LOG][/dim] {line.strip()}")
                    else:
                        time.sleep(0.5)
        except Exception:
            pass

    def run(self):
        # Boot health checks
        console.print("[bold green]Running Kernel Boot Sequence...[/bold green]")
        for skill in self.kernel.manifest.get("boot_sequence", []):
            console.print(f"[green]✔ {skill}[/green]")
            time.sleep(0.02)

        console.print(f"[green]✔ {len(self.kernel.registry)} functions loaded into registry[/green]")

        if self.kernel.evolution_llm:
            console.print(f"[green]✔ Evolution LLM: {self.kernel.config['providers']['evolution_api']['provider']}[/green]")
            try:
                console.print("[dim]  Testing Evolution LLM reachability...[/dim]")
                self.kernel.evolution_llm.complete([{"role": "user", "content": "ping"}], system="Reply 'pong'")
                console.print("[green]  ✔ Evolution LLM is reachable[/green]")
            except Exception as e:
                console.print(f"[bold red]  ✗ Evolution LLM Unreachable: {e}[/bold red]")
        else:
            console.print("[yellow]⚠ Evolution LLM not loaded (API key missing)[/yellow]")

        if self.kernel.meta_eval_llm:
            console.print(f"[green]✔ Meta-Eval LLM: {self.kernel.config['providers']['meta_eval_api']['provider']}[/green]")
            try:
                console.print("[dim]  Testing Meta-Eval LLM reachability...[/dim]")
                self.kernel.meta_eval_llm.complete([{"role": "user", "content": "ping"}], system="Reply 'pong'")
                console.print("[green]  ✔ Meta-Eval LLM is reachable[/green]")
            except Exception as e:
                console.print(f"[bold red]  ✗ Meta-Eval LLM Unreachable: {e}[/bold red]")
        else:
            console.print("[yellow]⚠ Meta-Eval LLM not loaded (API key missing)[/yellow]")

        console.print()

        # Start evolution loop in background
        kernel_thread = threading.Thread(target=self.run_kernel_loop, daemon=True)
        kernel_thread.start()

        # Director CLI
        session = PromptSession()
        console.print("[bold blue]Boros Director Interface[/bold blue]")
        console.print("Commands: 'boros status', 'boros pause', 'boros resume', or Ctrl+C to stop.")

        while True:
            try:
                with patch_stdout():
                    text = session.prompt("director> ")
                self.handle_command(text)
            except KeyboardInterrupt:
                console.print("[yellow]Shutting down...[/yellow]")
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
            console.print("[red]Commands must start with 'boros '[/red]")
            return

        cmd = text[6:].strip()
        if cmd == "status":
            state_file = self.boros_root / "session" / "loop_state.json"
            if state_file.exists():
                state = json.loads(state_file.read_text())
                console.print(f"[bold green]Loop State:[/bold green] {json.dumps(state, indent=2)}")
            else:
                console.print("[yellow]No active loop state.[/yellow]")
            console.print(f"[bold]Paused:[/bold] {self.pause_requested}")
            console.print(f"[bold]Registry:[/bold] {len(self.kernel.registry)} functions")
        elif cmd == "pause":
            self.pause_requested = True
            console.print("[yellow]Pause requested. Will stop at next cycle boundary.[/yellow]")
        elif cmd == "resume":
            if self.pause_requested:
                self.pause_requested = False
                kernel_thread = threading.Thread(target=self.run_kernel_loop, daemon=True)
                kernel_thread.start()
                console.print("[green]Resumed evolution loop.[/green]")
        else:
            with open(self.pending_file, "r") as f:
                data = json.load(f)
            data["pending"].append(cmd)
            with open(self.pending_file, "w") as f:
                json.dump(data, f, indent=2)
            console.print(f"[blue]Queued:[/blue] {cmd}")
