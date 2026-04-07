"""
Boros Unified Launcher
Starts the eval-generator and kernel together, managing both processes.
Usage: python run.py
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path

BOROS_ROOT = Path(__file__).parent
EVAL_GENERATOR = BOROS_ROOT / "eval-generator" / "eval_generator.py"
READY_FILE = BOROS_ROOT / "eval-generator" / "shared" / ".ready"
EVAL_READY_TIMEOUT = 30  # seconds to wait for eval-generator to be ready


def stream_output(proc, prefix, stop_event):
    """Stream subprocess output to stdout with a prefix label."""
    try:
        for line in iter(proc.stdout.readline, b""):
            if stop_event.is_set():
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            if text:
                print(f"[{prefix}] {text}", flush=True)
    except Exception:
        pass


def wait_for_eval_ready(timeout=EVAL_READY_TIMEOUT):
    """Poll for the eval-generator .ready file."""
    print(f"[LAUNCHER] Waiting for eval-generator to be ready (up to {timeout}s)...")
    for _ in range(timeout):
        if READY_FILE.exists():
            print("[LAUNCHER] Eval-generator is ready.")
            return True
        time.sleep(1)
    return False


def main():
    stop_event = threading.Event()
    eval_proc = None

    # ── Start eval-generator ──────────────────────────────────
    print("[LAUNCHER] Starting eval-generator...")
    try:
        eval_proc = subprocess.Popen(
            [sys.executable, str(EVAL_GENERATOR)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(BOROS_ROOT)
        )
        # Stream eval-generator logs in a background thread
        eval_thread = threading.Thread(
            target=stream_output,
            args=(eval_proc, "EVAL", stop_event),
            daemon=True
        )
        eval_thread.start()
    except FileNotFoundError:
        print(f"[LAUNCHER] ERROR: eval-generator not found at {EVAL_GENERATOR}")
        sys.exit(1)

    # Wait for eval-generator to signal it's ready
    if not wait_for_eval_ready():
        print("[LAUNCHER] WARNING: eval-generator did not signal ready in time.")
        print("[LAUNCHER] Continuing anyway — eval requests may time out if it's not running.")

    # ── Graceful shutdown on Ctrl+C / SIGTERM ────────────────
    def shutdown(signum=None, frame=None):
        print("\n[LAUNCHER] Shutting down...")
        stop_event.set()
        if eval_proc and eval_proc.poll() is None:
            eval_proc.terminate()
            try:
                eval_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                eval_proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # ── Start kernel ─────────────────────────────────────────
    print("[LAUNCHER] Starting Boros kernel...")
    try:
        # Ensure project root is importable
        sys.path.insert(0, str(BOROS_ROOT.parent))

        from boros.kernel import BorosKernel
        import importlib

        kernel = BorosKernel()

        # Check eval-generator health before entering director
        if eval_proc.poll() is not None:
            print("[LAUNCHER] WARNING: eval-generator process has already exited!")

        interface_module = importlib.import_module("boros.skills.director-interface.functions.interface")
        ui = interface_module.DirectorInterface(kernel)
        ui.run()

    except KeyboardInterrupt:
        shutdown()
    except Exception as e:
        print(f"[LAUNCHER] FATAL: Kernel failed to start: {e}")
        import traceback
        traceback.print_exc()
        shutdown()


if __name__ == "__main__":
    main()
