"""
Director Interface — Boros TUI
Clean, minimal terminal interface with plain text.
"""

import threading
import time
import json
import datetime
import sys
from pathlib import Path


class DirectorInterface:
    
    def __init__(self, kernel):
        self.kernel = kernel
        self.boros_root = kernel.boros_root
        self.pause_requested = False
        self.verbose = False
        self._agent_loop = None
        
        # Ensure dirs
        self.logs_dir = self.boros_root / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.cycles_log = self.logs_dir / "cycles.log"
        if not self.cycles_log.exists():
            self.cycles_log.write_text("")
    
    def log(self, msg):
        """Log to file."""
        try:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            with open(self.cycles_log, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {msg}\n")
        except Exception:
            pass
    
    def run(self):
        """Main loop."""
        # Start kernel loop in background
        threading.Thread(target=self.run_kernel_loop, daemon=True).start()
        
        # Simple command loop
        while True:
            try:
                text = input("boros> ").strip()
                if text:
                    self._dispatch(text)
            except (KeyboardInterrupt, EOFError):
                self._quit()
    
    def _dispatch(self, raw):
        """Parse and run command."""
        parts = raw.strip().split()
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd in ("s", "st"):
            self._status()
        elif cmd in ("p"):
            self._pause()
        elif cmd in ("r"):
            self._resume()
        elif cmd in ("e"):
            self._set_mode("evolution")
        elif cmd in ("w"):
            self._set_mode("employee")
        elif cmd == "fork":
            self._fork()
        elif cmd == "rev":
            self._revolve()
        elif cmd in ("l"):
            self._logs(int(args[0]) if args and args[0].isdigit() else 10)
        elif cmd in ("sk"):
            self._skills()
        elif cmd in ("sc"):
            self._scores()
        elif cmd == "v":
            self._toggle_verbose()
        elif cmd in ("h", "?"):
            self._help()
        elif cmd in ("q"):
            self._quit()
        else:
            print("  Unknown: " + cmd + " — type help")
    
    def _status(self):
        """Show current status."""
        state_file = self.boros_root / "session" / "loop_state.json"
        hw_file = self.boros_root / "skills" / "eval-bridge" / "state" / "high_water_marks.json"
        
        state = json.loads(state_file.read_text()) if state_file.exists() else {}
        hw = json.loads(hw_file.read_text()) if hw_file.exists() else {}
        
        mode = state.get("agent_state", state.get("mode", "evolution"))
        cycle = state.get("cycle", 0)
        gen = state.get("generation", 0)
        paused = "PAUSED" if self.pause_requested else "RUNNING"
        
        print()
        print("  " + "-" * 50)
        print("  B.O.R.O.S  |  " + mode + "  |  c" + str(cycle) + "  |  g" + str(gen) + "  |  " + paused)
        
        if hw:
            score_parts = []
            for k, v in sorted(hw.items()):
                if isinstance(v, (int, float)) and v > 0:
                    score_parts.append(k + ":" + str(v)[:4])
            if score_parts:
                print("  Scores:  " + "  ".join(score_parts))
        
        print("  " + "-" * 50)
        print()
    
    def _pause(self):
        if self.pause_requested:
            print("  Already paused")
            return
        self.pause_requested = True
        print("  Pausing after cycle...")
    
    def _resume(self):
        if not self.pause_requested:
            print("  Not paused")
            return
        self.pause_requested = False
        threading.Thread(target=self.run_kernel_loop, daemon=True).start()
        print("  Resumed")
    
    def _set_mode(self, mode):
        state_file = self.boros_root / "session" / "loop_state.json"
        if not state_file.exists():
            print("  No active session")
            return
        try:
            state = json.loads(state_file.read_text())
            state["mode"] = mode
            state_file.write_text(json.dumps(state, indent=2))
        except Exception:
            pass
        if self._agent_loop:
            self._agent_loop.interrupt_requested = True
        print("  Mode: " + mode)
    
    def _logs(self, n=10):
        log_file = self.logs_dir / "cycles.log"
        if not log_file.exists() or log_file.stat().st_size == 0:
            print("  No logs")
            return
        try:
            lines = [l for l in log_file.read_text(encoding="utf-8").strip().split("\n") if l.strip()][-n:]
            print()
            for l in lines:
                print("  " + l)
            print()
        except Exception:
            pass
    
    def _skills(self):
        print()
        for name, info in self.kernel.manifest.get("skills", {}).items():
            fns = info.get("provided_functions", [])
            print("  " + name + "  (" + str(len(fns)) + " fns)")
        print()
    
    def _scores(self):
        hw_file = self.boros_root / "skills" / "eval-bridge" / "state" / "high_water_marks.json"
        if not hw_file.exists():
            print("  No scores yet")
            return
        hw = json.loads(hw_file.read_text())
        print()
        for k, v in sorted(hw.items()):
            if isinstance(v, (int, float)):
                bar = "#" * int(v * 10) + "-" * (10 - int(v * 10))
                star = " *" if v > 0.7 else ""
                print("  " + k[:15].ljust(15) + " " + str(v)[:5] + star + " [" + bar + "]")
        print()
    
    def _toggle_verbose(self):
        self.verbose = not self.verbose
        state = "on" if self.verbose else "off"
        print("  verbose " + state)
    
    def _help(self):
        print()
        print("  B.O.R.O.S Commands")
        print()
        print("  s          status")
        print("  p          pause")
        print("  r          resume")
        print("  " + "-" * 50)
        print("  e          evolve mode")
        print("  w          work mode")
        print("  fork       fork as agent")
        print("  rev        re-evolve")
        print("  " + "-" * 50)
        print("  l [n]      logs (last n)")
        print("  sk         skills")
        print("  sc         scores")
        print("  " + "-" * 50)
        print("  v          toggle verbose")
        print("  h          help")
        print("  q          quit")
        print()
    
    def _fork(self):
        state_file = self.boros_root / "session" / "loop_state.json"
        if not state_file.exists():
            print("  No active session")
            return
        state = json.loads(state_file.read_text())
        
        lineage_file = self.boros_root / "lineage.json"
        lineage = {"entries": []}
        if lineage_file.exists():
            try:
                lineage = json.loads(lineage_file.read_text())
            except Exception:
                pass
        
        gen = sum(1 for e in lineage.get("entries", []) if e.get("event") == "fork")
        
        lineage["entries"].append({
            "event": "fork", "generation": gen,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "cycle_at_fork": state.get("cycle", 0),
        })
        lineage_file.write_text(json.dumps(lineage, indent=2))
        
        state["mode"] = "employee"
        state["agent_state"] = "boros-fork"
        state["generation"] = gen
        state_file.write_text(json.dumps(state, indent=2))
        
        print("  Forked g" + str(gen))
    
    def _revolve(self):
        state_file = self.boros_root / "session" / "loop_state.json"
        if not state_file.exists():
            print("  No active session")
            return
        state = json.loads(state_file.read_text())
        state["mode"] = "evolution"
        state["agent_state"] = "evolution"
        state_file.write_text(json.dumps(state, indent=2))
        
        self.pause_requested = False
        threading.Thread(target=self.run_kernel_loop, daemon=True).start()
        print("  Re-evolving...")
    
    def run_kernel_loop(self):
        if self.kernel.evolution_llm is None:
            print("  No LLM")
            return
        from agent_loop import AgentLoop
        loop = AgentLoop(self.kernel, log_callback=self.log)
        self._agent_loop = loop
        try:
            loop.run_continuous(
                should_pause=lambda: self.pause_requested,
                on_cycle_complete=lambda num, tc: self.log(f"cycle {num} done")
            )
        except Exception as e:
            self.log(f"error: {e}")
    
    def _quit(self):
        self.pause_requested = True
        print()
        print("  Stopping...")
        sys.exit(0)