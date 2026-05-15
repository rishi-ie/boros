"""
Director Interface — Simple Boros CLI.
Rich-based, slash commands, natural language input.
"""

import threading
import json
import datetime
import sys
import re
from pathlib import Path


# ── ANSI helpers ────────────────────────────────────────────────────────────

def W(s): return f"\x1b[97m{s}\x1b[0m"
def D(s): return f"\x1b[2m{s}\x1b[0m"
def A(s): return f"\x1b[94m{s}\x1b[0m"
def G(s): return f"\x1b[32m{s}\x1b[0m"
def Y(s): return f"\x1b[33m{s}\x1b[0m"
def R(s): return f"\x1b[31m{s}\x1b[0m"


def vw(s):
    return len(re.sub(r'\x1b\[[0-9;]*m', '', s))


# ── Logo ──────────────────────────────────────────────────────────────────────

LOGO = """
\x1b[97m██████╗  ██████╗ ██████╗  ██████╗ ███████╗\x1b[0m
\x1b[97m██╔══██╗██╔═══██╗██╔══██╗██╔═══██╗██╔════╝\x1b[0m
\x1b[97m██████╔╝██║   ██║██████╔╝██║   ██║███████╗\x1b[0m
\x1b[97m██╔══██╗██║   ██║██╔══██╗██║   ██║╚════██║\x1b[0m
\x1b[97m██████╔╝╚██████╔╝██║  ██║╚██████╔╝███████║\x1b[0m
\x1b[97m╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝\x1b[0m"""


# ── Main interface ────────────────────────────────────────────────────────────

class DirectorInterface:

    def __init__(self, kernel):
        self.kernel = kernel
        self.boros_root = kernel.boros_root
        self.pause_requested = False
        self.verbose = False
        self._agent_loop = None
        self._boot_time = datetime.datetime.now()

        self.logs_dir = self.boros_root / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.cycles_log = self.logs_dir / "cycles.log"
        if not self.cycles_log.exists():
            self.cycles_log.write_text("")

    def log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        try:
            with open(self.cycles_log, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {msg}\n")
        except Exception:
            pass

    # ── Render ───────────────────────────────────────────────────────────────

    def render(self, tw=None):
        """Print the full status display (used by /status)."""
        if tw is None:
            try:
                tw = __import__('os').get_terminal_size().columns
            except Exception:
                tw = 80

        state = self._read_state()
        hw = self._read_hw()

        cycle = state.get("cycle", 0)
        mode = state.get("agent_state", state.get("mode", "evolution"))
        gen = state.get("generation", 0)
        paused = "PAUSED" if self.pause_requested else "RUNNING"

        status_right = (
            W("B.O.R.O.S") + "  " + A(mode) + "  "
            + D(f"c{cycle}") + "  " + D(f"g{gen}") + "  "
            + f"\x1b[36mminimax\x1b[0m" + "  " + D("M2.7")
        )

        out = []

        # Logo top + status
        out.append(self._pad(W(LOGO.split("\n")[1]), status_right, tw))
        for line in LOGO.split("\n")[2:]:
            out.append(self._pad(W(line), "", tw))

        out.append("")
        out.append(W("─" * tw))

        # Status bar
        ps = G("RUNNING") if paused == "RUNNING" else Y("PAUSED")
        sk = len(self.kernel.manifest.get("skills", {}))
        fn = len(self.kernel.registry)
        out.append(
            W("B.O.R.O.S") + "  " + A(mode) + "  "
            + D(f"c{cycle}") + "  " + D("|") + "  "
            + f"\x1b[36mminimax\x1b[0m" + "  " + D("|") + "  "
            + ps + "  " + D("|") + "  "
            + D(f"{sk} skills · {fn} fns")
        )
        out.append(W("─" * tw))

        # Scores | Agents | Meta | Version
        hw_items = sorted(hw.items(), key=lambda x: x[1], reverse=True)[:7]
        for i in range(7):
            score_line = ""
            if i < len(hw_items):
                k, v = hw_items[i]
                if isinstance(v, (int, float)):
                    b = "█" * int(v * 6) + "░" * (6 - int(v * 6))
                    c = G if v > 0.7 else (Y if v > 0.3 else D)
                    score_line = f"  {c(b)} {v:.2f}  {D(k[:14])}"

            agents_line = self._agents_line(i)
            meta_line = self._meta_line(i)
            vc_line = self._vc_line(i)

            line = score_line + W("  ") + agents_line + W("  ") + meta_line + W("  ") + vc_line
            if vw(line) > tw:
                line = line[:tw]
            out.append(line)

        out.append(W("─" * tw))
        out.append(D("  /status  /scores  /skills  /logs  /help"))

        return "\n".join(out)

    def _pad(self, left, right, width):
        l = vw(left)
        r = vw(right)
        gap = max(1, width - l - r)
        return left + " " * gap + right

    def _read_state(self):
        f = self.boros_root / "session" / "loop_state.json"
        if f.exists():
            try:
                return json.loads(f.read_text())
            except Exception:
                pass
        return {}

    def _read_hw(self):
        f = self.boros_root / "skills" / "eval-bridge" / "state" / "high_water_marks.json"
        if f.exists():
            try:
                return json.loads(f.read_text())
            except Exception:
                pass
        return {}

    def _agents_line(self, i):
        rows = [
            "  reflect  | 0 hyp, 0 pending",
            "  architect| 0 prop, 0 rev",
            "  reviewer | 0 rej, 0 blocked",
            "  ", "  ", "  ", "  ",
        ]
        return D(rows[i] if i < len(rows) else "")

    def _meta_line(self, i):
        rows = ["  best: none", "  tracking...", "  blocked: none", "  ", "  ", "  ", "  "]
        return D(rows[i] if i < len(rows) else "")

    def _vc_line(self, i):
        rows = ["  0 snapshots", "  ", "  ", "  ", "  ", "  ", "  "]
        return D(rows[i] if i < len(rows) else "")

    # ── Dispatch ─────────────────────────────────────────────────────────────

    def dispatch(self, text):
        text = text.strip()
        if not text:
            return

        if text.startswith("/"):
            self._cmd(text[1:])
        else:
            self._evolve(text)

    def _evolve(self, goal):
        """Queue a goal and trigger an evolution cycle."""
        goal_file = self.boros_root / "session" / "pending_goal.txt"
        with open(goal_file, "w", encoding="utf-8") as f:
            f.write(goal)
        self.log(f"[USER GOAL] {goal}")
        print(f"\n  {G('◉')} queued: {goal[:60]}...\n  {D('running evolution cycle...')}\n")
        # Start kernel loop if not running
        if not self._agent_loop:
            threading.Thread(target=self.run_kernel_loop, daemon=True).start()

    def _cmd(self, raw):
        parts = raw.strip().split()
        if not parts:
            return
        cmd = parts[0].lower()
        args = parts[1:]

        CMDS = {
            "s": self._status, "status": self._status,
            "p": self._pause, "pause": self._pause,
            "r": self._resume, "resume": self._resume,
            "e": lambda a: self._set_mode("evolution"), "evolve": lambda a: self._set_mode("evolution"),
            "w": lambda a: self._set_mode("employee"), "work": lambda a: self._set_mode("employee"),
            "fork": self._fork,
            "rev": self._revolve, "revolve": self._revolve,
            "snap": lambda a: self._snapshot(a),
            "scores": self._scores, "sc": self._scores,
            "skills": self._skills, "sk": self._skills,
            "logs": lambda a: self._logs(int(a[0]) if a and a[0].isdigit() else 10),
            "l": lambda a: self._logs(10),
            "h": self._help, "help": self._help,
            "q": self._quit, "quit": self._quit, "exit": self._quit,
            "who": self._who,
            "env": self._env,
            "cycles": self._cycles,
            "clear": lambda a: print(self._cls()),
        }

        handler = CMDS.get(cmd)
        if handler:
            if callable(handler) and hasattr(handler, '__name__') and handler.__name__ == '<lambda>':
                handler(args)
            elif callable(handler):
                handler()
        else:
            print(f"\n  {R('unknown:')} /{cmd}  — type /help\n")

    # ── Command handlers ────────────────────────────────────────────────────

    def _status(self):
        print(self.render())

    def _pause(self):
        if self.pause_requested:
            print(f"\n  {Y('already paused')}\n")
            return
        self.pause_requested = True
        print(f"\n  {Y('pausing after cycle...')}\n")

    def _resume(self):
        if not self.pause_requested:
            print(f"\n  {Y('not paused')}\n")
            return
        self.pause_requested = False
        threading.Thread(target=self.run_kernel_loop, daemon=True).start()
        print(f"\n  {G('resumed')}\n")

    def _set_mode(self, mode):
        f = self.boros_root / "session" / "loop_state.json"
        if not f.exists():
            print(f"\n  {Y('no active session')}\n")
            return
        try:
            state = json.loads(f.read_text())
            state["mode"] = mode
            f.write_text(json.dumps(state, indent=2))
            print(f"\n  mode: {A(mode)}\n")
        except Exception as e:
            print(f"\n  {R('error:')} {e}\n")

    def _fork(self):
        f = self.boros_root / "session" / "loop_state.json"
        if not f.exists():
            print(f"\n  {Y('no active session')}\n")
            return
        state = json.loads(f.read_text())
        lf = self.boros_root / "lineage.json"
        lineage = json.loads(lf.read_text()) if lf.exists() else {"entries": []}
        gen = sum(1 for e in lineage.get("entries", []) if e.get("event") == "fork")
        lineage["entries"].append({
            "event": "fork", "generation": gen,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "cycle_at_fork": state.get("cycle", 0),
        })
        lf.write_text(json.dumps(lineage, indent=2))
        state["mode"] = "employee"
        state["agent_state"] = "boros-fork"
        state["generation"] = gen
        f.write_text(json.dumps(state, indent=2))
        print(f"\n  {G('forked')} g{gen}\n")

    def _revolve(self):
        f = self.boros_root / "session" / "loop_state.json"
        if not f.exists():
            print(f"\n  {Y('no active session')}\n")
            return
        state = json.loads(f.read_text())
        state["mode"] = "evolution"
        state["agent_state"] = "evolution"
        f.write_text(json.dumps(state, indent=2))
        self.pause_requested = False
        threading.Thread(target=self.run_kernel_loop, daemon=True).start()
        print(f"\n  {G('re-evolving...')}\n")

    def _snapshot(self, args):
        label = args[0] if args else ""
        state = self._read_state()
        try:
            from version_control import VersionControl
            vc = VersionControl(self.boros_root)
            snap_id = vc.snapshot(label=label, cycle=state.get("cycle", 0))
            print(f"\n  {G('snapshot:')} {snap_id[:40]}\n")
        except Exception as e:
            print(f"\n  {R('error:')} {e}\n")

    def _scores(self):
        hw = self._read_hw()
        print()
        for k, v in sorted(hw.items(), key=lambda x: x[1], reverse=True):
            if isinstance(v, (int, float)):
                b = "█" * int(v * 8) + "░" * (8 - int(v * 8))
                star = G("★") if v > 0.7 else ""
                c = G if v > 0.7 else (Y if v > 0.3 else D)
                print(f"  {k[:15].ljust(15)} {c(f'{v:.3f}')}{star} [{c(b)}]")
        print()

    def _skills(self):
        print()
        for name, info in sorted(self.kernel.manifest.get("skills", {}).items()):
            fns = info.get("provided_functions", [])
            print(f"  {A(name):<30} {D(f'({len(fns)} fns)')}")
        print()

    def _logs(self, n=10):
        if not self.cycles_log.exists() or self.cycles_log.stat().st_size == 0:
            print(f"\n  {D('no logs')}\n")
            return
        try:
            lines = [l for l in self.cycles_log.read_text(encoding="utf-8").strip().split("\n") if l.strip()][-n:]
            print()
            for l in lines:
                print(f"  {D(l)}")
            print()
        except Exception as e:
            print(f"\n  {R('error:')} {e}\n")

    def _who(self):
        identity = self.kernel.identity or {}
        print()
        for k, v in identity.items():
            print(f"  {A(k):<20} {v}")
        if not identity:
            print(f"  {D('no identity set yet')}")
        print()

    def _env(self):
        state = self._read_state()
        print()
        print(f"  {W('Model:')}      {A('MiniMax-M2.7')}")
        print(f"  {W('Provider:')}     {A('minimax')}")
        print(f"  {W('Skills:')}       {len(self.kernel.manifest.get('skills', {}))}")
        print(f"  {W('Functions:')}    {len(self.kernel.registry)}")
        print(f"  {W('Cycle:')}        {state.get('cycle', 0)}")
        print(f"  {W('Mode:')}         {state.get('mode', 'evolution')}")
        print()

    def _cycles(self):
        state = self._read_state()
        print()
        print(f"  cycle       : {state.get('cycle', 0)}")
        print(f"  mode        : {state.get('mode', 'unknown')}")
        print(f"  agent_state : {state.get('agent_state', 'unknown')}")
        print(f"  generation  : {state.get('generation', 0)}")
        print(f"  started_at  : {state.get('started_at', 'unknown')}")
        print()

    def _help(self):
        print(f"""
{A('B.O.R.O.S Commands')}

{A('Core:')}
  /status     s       current state
  /pause      p       pause after cycle
  /resume     r       resume from pause

{A('Lifecycle:')}
  /evolve     e       switch to evolution mode
  /work       w       switch to work mode
  /fork               fork as deployment agent
  /revolve    rev     re-evolve from fork

{A('Version Control:')}
  /snap [label]       create snapshot
  /scores     sc      capability scores
  /skills     sk      list all skills

{A('Info:')}
  /logs [n]   l       logs (last n, default 10)
  /who                who am i
  /env                environment info
  /cycles             cycle history

{A('System:')}
  /help       h       this help
  /clear              clear screen
  /quit       q       exit

{A('Usage:')}
  type naturally to start an evolution cycle with that goal
""")

    def _quit(self):
        self.pause_requested = True
        print(f"\n  {D('stopping...')}\n")
        sys.exit(0)

    # ── Kernel loop ─────────────────────────────────────────────────────────

    def run_kernel_loop(self):
        if self._agent_loop:
            return
        if self.kernel.evolution_llm is None:
            print(f"\n  {R('no LLM — check .env')}\n")
            return
        from agent_loop import AgentLoop
        self._agent_loop = AgentLoop(self.kernel, log_callback=self.log)
        try:
            self._agent_loop.run_continuous(
                should_pause=lambda: self.pause_requested,
                on_cycle_complete=lambda num, tc: self.log(f"cycle {num} done")
            )
        except Exception as e:
            self.log(f"error: {e}")

    # ── Run ─────────────────────────────────────────────────────────────────

    def run(self):
        threading.Thread(target=self.run_kernel_loop, daemon=True).start()
        print(f"  {G('●')} ready  ·  minimax  ·  {len(self.kernel.manifest.get('skills', {}))} skills")
        print(f"  {D('/help for commands  \u00b7  type naturally to evolve')}")
        print()

        while True:
            try:
                text = input(f"\n{W('boros')} {D('>')} ")
                if text.strip():
                    self.dispatch(text)
            except (KeyboardInterrupt, EOFError):
                self._quit()