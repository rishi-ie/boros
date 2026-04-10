"""
start.py — Launch Boros.

Usage:
    python start.py
"""
import subprocess
import sys
import time
import io
import json
import contextlib
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent))


def main():
    from rich.console import Console
    from rich.text import Text
    from rich.panel import Panel
    from rich.align import Align
    from rich.progress import Progress, SpinnerColumn, TextColumn

    console = Console()

    # ── Banner ───────────────────────────────────────────────────────────────
    logo = (
        "██████╗  ██████╗ ██████╗  ██████╗ ███████╗\n"
        "██╔══██╗██╔═══██╗██╔══██╗██╔═══██╗██╔════╝\n"
        "██████╔╝██║   ██║██████╔╝██║   ██║███████╗\n"
        "██╔══██╗██║   ██║██╔══██╗██║   ██║╚════██║\n"
        "██████╔╝╚██████╔╝██║  ██║╚██████╔╝███████║\n"
        "╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝"
    )
    text = Text(logo, style="bold cyan")
    text.append("\n\nSelf-Evolving Agent  ·  ARES", style="dim")
    console.print(Panel(Align.center(text), border_style="cyan", padding=(1, 2)))
    console.print()

    # ── Boot ─────────────────────────────────────────────────────────────────
    eval_proc = None
    kernel    = None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Starting eval engine...", total=None)

        # Launch eval-generator — allow logs to be visible to the user
        eval_proc = subprocess.Popen(
            [sys.executable, str(ROOT / "eval-generator" / "eval_generator.py")],
            cwd=str(ROOT)
        )
        ready_file = ROOT / "eval-generator" / "shared" / ".ready"
        for _ in range(30):
            if ready_file.exists():
                break
            time.sleep(1)

        progress.update(task, description="Loading kernel...")

        # Boot kernel — capture its stdout so it doesn't bleed through the spinner
        _captured = io.StringIO()
        try:
            with contextlib.redirect_stdout(_captured):
                from boros.kernel import BorosKernel
                kernel = BorosKernel()
        except SystemExit:
            progress.stop()
            console.print("\n  [bold red]✗  Boot failed — missing or invalid API key.[/bold red]\n")
            console.print("  Copy [cyan].env.template[/cyan] → [cyan].env[/cyan] and add your key:\n")
            console.print("      [dim]GEMINI_API_KEY=your_key_here[/dim]")
            console.print("   or [dim]ANTHROPIC_API_KEY=your_key_here[/dim]\n")
            if eval_proc:
                eval_proc.terminate()
            return

        progress.update(task, description="Checking connectivity...")

        llm_ok  = True
        llm_err = ""
        try:
            kernel.evolution_llm.complete(
                [{"role": "user", "content": "ping"}],
                system="Reply 'pong'"
            )
        except Exception as e:
            llm_ok  = False
            llm_err = str(e)[:80]

        progress.update(task, description="Ready.")
        time.sleep(0.2)

    # ── Boot summary ─────────────────────────────────────────────────────────
    provider = kernel.config["providers"]["evolution_api"]["provider"]
    model    = kernel.config["providers"]["evolution_api"]["model"]

    if llm_ok:
        console.print(f"  [green]✔[/green]  {provider}  ·  {model}")
    else:
        console.print(f"  [yellow]⚠[/yellow]  {provider} unreachable — {llm_err}")

    skill_count    = len(kernel.manifest.get("skills", {}))
    registry_count = len(kernel.registry)
    console.print(f"  [green]✔[/green]  {registry_count} functions  ·  {skill_count} skills loaded")

    # Show current state if returning
    state_file = ROOT / "session" / "loop_state.json"
    hw_file    = ROOT / "skills" / "eval-bridge" / "state" / "high_water_marks.json"
    if state_file.exists():
        try:
            state  = json.loads(state_file.read_text())
            cycle  = state.get("cycle", 0)
            mode   = state.get("agent_state", state.get("mode", "evolution"))
            scores = ""
            if hw_file.exists():
                hw    = json.loads(hw_file.read_text())
                parts = [f"{k} {v:.3f}" for k, v in hw.items() if isinstance(v, (int, float)) and v > 0]
                if parts:
                    scores = "  ·  " + "  ".join(parts)
            console.print(f"  [green]✔[/green]  Cycle {cycle}  ·  {mode}{scores}")
        except Exception:
            pass

    console.print()
    console.print("  [dim]Type[/dim] [bold]help[/bold] [dim]to see commands.[/dim]")
    console.print()

    # ── Hand off to interface ─────────────────────────────────────────────────
    try:
        import importlib
        iface = importlib.import_module("boros.skills.director-interface.functions.interface")
        ui = iface.DirectorInterface(kernel)
        ui.run()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if eval_proc:
            eval_proc.terminate()
            try:
                eval_proc.wait(timeout=5)
            except Exception:
                pass
        console.print("\n  Stopped.\n")


if __name__ == "__main__":
    main()
