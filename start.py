"""
start.py — Launch Boros kernel + eval-generator together.

Usage:
    python start.py
"""
import subprocess
import sys
import os
import time
from pathlib import Path

ROOT = Path(__file__).parent


def main():
    print("[start] Launching eval-generator...")
    eval_proc = subprocess.Popen(
        [sys.executable, str(ROOT / "eval-generator" / "eval_generator.py")],
        cwd=str(ROOT),
    )

    # Wait for eval-generator to signal readiness (writes .ready file)
    ready_file = ROOT / "eval-generator" / "shared" / ".ready"
    for _ in range(30):
        if ready_file.exists():
            print("[start] Eval-generator ready.")
            break
        time.sleep(1)
    else:
        print("[start] WARNING: eval-generator did not signal ready after 30s — continuing anyway.")

    print("[start] Launching Boros kernel...")
    try:
        from boros.kernel import BorosKernel
        import importlib
        kernel = BorosKernel()
        interface_module = importlib.import_module("boros.skills.director-interface.functions.interface")
        ui = interface_module.DirectorInterface(kernel)
        ui.run()
    except KeyboardInterrupt:
        print("\n[start] Shutting down...")
    finally:
        eval_proc.terminate()
        eval_proc.wait(timeout=5)
        print("[start] Eval-generator stopped.")


if __name__ == "__main__":
    main()
