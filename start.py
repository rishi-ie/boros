"""
start.py — Launch Boros.
"""
import subprocess
import sys
import time
import io
import json
import contextlib
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


# ══════════════════════════════════════════════════════════════════════════════════════
# LOGO (single, #EEADA0)
# ══════════════════════════════════════════════════════════════════════════════════════

LOGO = """
██████╗  ██████╗ ██████╗  ██████╗ ███████╗
██╔══██╗██╔═══██╗██╔══██╗██╔═══██╗██╔════╝
██████╔╝██║   ██║██████╔╝██║   ██║███████╗
██╔══██╗██║   ██║██╔══██╗██║   ██║╚════██║
██████╔╝╚██████╔╝██║  ██║╚██████╔╝███████║
╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
"""


# ══════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════════════

def main():
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    
    from rich.console import Console
    from rich.panel import Panel
    from rich.align import Align
    from rich.text import Text
    
    console = Console()
    
    # ── LOGO ─────────────────────────────────────────────────────────────────────
    text = Text(LOGO, style="#EEADA0 bold")
    text.append("\nSelf-Evolving Agent  ·  ARES", style="dim")
    console.print(Panel(Align.center(text), border_style="#EEADA0", padding=(1, 2)))
    console.print()
    
    # ── BOOT ─────────────────────────────────────────────────────────────────────
    eval_proc = None
    kernel = None
    
    from rich.progress import Progress, SpinnerColumn, TextColumn
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
        task = progress.add_task("", start=False)
        
        # Launch eval engine
        progress.update(task, description="Starting eval engine...", completed=10)
        eval_proc = subprocess.Popen(
            [sys.executable, str(ROOT / "eval-generator" / "eval_generator.py")],
            cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        ready_file = ROOT / "eval-generator" / "shared" / ".ready"
        for _ in range(30):
            if ready_file.exists():
                break
            time.sleep(1)
        
        # Boot kernel
        progress.update(task, description="Loading kernel...", completed=40)
        _captured = io.StringIO()
        try:
            with contextlib.redirect_stdout(_captured):
                from kernel import BorosKernel
                kernel = BorosKernel()
        except SystemExit:
            console.print("\n  [bold red]X  Boot failed — missing API key.[/bold red]")
            console.print("  Add GEMINI_API_KEY or ANTHROPIC_API_KEY to .env")
            if eval_proc:
                eval_proc.terminate()
            return
        
        # Check LLM
        progress.update(task, description="Checking LLM...", completed=70)
        try:
            kernel.evolution_llm.complete([{"role": "user", "content": "ping"}], system="Reply 'pong'")
        except Exception as e:
            console.print(f"\n  [yellow]!  LLM unreachable: {str(e)[:60]}[/yellow]")
        
        progress.update(task, description="Ready", completed=100)
        time.sleep(0.2)
    
    # ── STATUS LINE ─────────────────────────────────────────────────────────────
    provider = kernel.config["providers"]["evolution_api"]["provider"]
    model = kernel.config["providers"]["evolution_api"]["model"]
    skill_count = len(kernel.manifest.get("skills", {}))
    
    state_file = ROOT / "session" / "loop_state.json"
    hw_file = ROOT / "skills" / "eval-bridge" / "state" / "high_water_marks.json"
    
    mode = "evolution"
    cycle = 0
    
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
            cycle = state.get("cycle", 0)
            mode = state.get("agent_state", state.get("mode", "evolution"))
        except Exception:
            pass
    
    # Clean status line
    console.print(f"  [dim]B.O.R.O.S[/dim]  [cyan]{mode}[/cyan]  [dim]|[/dim]  [white]c{cycle}[/white]  [dim]|[/dim]  [white]{provider}[/white]  [dim]|[/dim]  [dim]{skill_count} skills[/dim]")
    console.print()
    
    # ── HAND OFF ────────────────────────────────────────────────────────────────
    try:
        import importlib
        iface = importlib.import_module("skills.director-interface.functions.interface")
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
        console.print("\n  [dim]Stopped.[/dim]")


if __name__ == "__main__":
    main()