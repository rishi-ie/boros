"""
start.py — Launch Boros.
Simple boot: logo, kernel, hand off to DirectorInterface.
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


# Logo (original Unicode block art, white)
LOGO = """
██████╗  ██████╗ ██████╗  ██████╗ ███████╗
██╔══██╗██╔═══██╗██╔══██╗██╔═══██╗██╔════╝
██████╔╝██║   ██║██████╔╝██║   ██║███████╗
██╔══██╗██║   ██║██╔══██╗██║   ██║╚════██║
██████╔╝╚██████╔╝██║  ██║╚██████╔╝███████║
╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
""".strip()


def main():
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    # Print loading
    print(f"\x1b[97m{LOGO}\x1b[0m")
    print(f"  \x1b[2mself-evolving agent  ·  ARES\x1b[0m")
    print(f"  \x1b[2mloading...\x1b[0m")
    print()

    eval_proc = None
    kernel = None

    try:
        # Launch eval engine
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
        _cap = io.StringIO()
        try:
            with contextlib.redirect_stdout(_cap):
                from kernel import BorosKernel
                kernel = BorosKernel()
        except SystemExit:
            print(f"\n  \x1b[91mFATAL: Missing API key. Add MINIMAX_API_KEY to .env\x1b[0m\n")
            if eval_proc:
                eval_proc.terminate()
            return

        # LLM check
        try:
            kernel.evolution_llm.complete(
                [{"role": "user", "content": "ping"}],
                system="Reply 'pong'"
            )
            print(f"  \x1b[92mLLM ready\x1b[0m  \x1b[90m·\x1b[0m  \x1b[94m{kernel.config['providers']['evolution_api']['model']}\x1b[0m")
            print(f"  \x1b[90m{len(kernel.manifest.get('skills', {}))} skills loaded\x1b[0m")
        except Exception as e:
            print(f"  \x1b[93mWARNING: {str(e)[:80]}\x1b[0m")

    except Exception as e:
        print(f"\n  \x1b[91mFATAL: {e}\x1b[0m\n")
        return

    print()

    # Hand off
    try:
        import importlib
        iface = importlib.import_module("skills.director_interface.functions.interface")
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
        print("\n  \x1b[90mstopped.\x1b[0m\n")


if __name__ == "__main__":
    main()