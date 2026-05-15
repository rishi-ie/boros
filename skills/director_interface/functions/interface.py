"""
Director Interface — Boros TUI
Clean, minimal terminal interface. Proper agentic CLI.
"""

import threading
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

        # Systems (lazy-loaded)
        self._meta_model = None
        self._metacognition = None
        self._version_control = None
        self._capability_graph = None

        # Ensure dirs
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

    def run(self):
        threading.Thread(target=self.run_kernel_loop, daemon=True).start()
        while True:
            try:
                text = input("boros> ").strip()
                if text:
                    self._dispatch(text)
            except (KeyboardInterrupt, EOFError):
                self._quit()

    def _dispatch(self, raw):
        parts = raw.strip().split()
        if not parts:
            return
        cmd = parts[0].lower()
        args = parts[1:]

        # Core
        if cmd in ("s", "st"):
            self._status()
        elif cmd in ("p",):
            self._pause()
        elif cmd in ("r",):
            self._resume()

        # Mode / lifecycle
        elif cmd in ("e",):
            self._set_mode("evolution")
        elif cmd in ("w",):
            self._set_mode("employee")
        elif cmd == "fork":
            self._fork()
        elif cmd == "rev":
            self._revolve()

        # New systems (blueprint v2)
        elif cmd in ("ag", "agents"):
            self._agents()
        elif cmd in ("wm", "world"):
            self._world_model()
        elif cmd in ("mc", "meta"):
            self._metacog()
        elif cmd in ("ml", "metalearn"):
            self._metalearn()
        elif cmd in ("vc",):
            self._version()
        elif cmd == "snap":
            self._snapshot(args)
        elif cmd == "diff":
            self._diff(args)
        elif cmd == "rollback":
            self._rollback(args)
        elif cmd in ("cp", "comp"):
            self._composition()
        elif cmd in ("perf",):
            self._perf()

        # Info
        elif cmd in ("l",):
            self._logs(int(args[0]) if args and args[0].isdigit() else 10)
        elif cmd in ("sk",):
            self._skills()
        elif cmd in ("sc",):
            self._scores()
        elif cmd == "v":
            self._toggle_verbose()
        elif cmd in ("h", "?"):
            self._help()
        elif cmd in ("q",):
            self._quit()
        else:
            print("  Unknown: " + cmd + " — type h for help")

    # ── Core Commands ─────────────────────────────────────────────────────────

    def _status(self):
        state_file = self.boros_root / "session" / "loop_state.json"
        hw_file = self.boros_root / "skills" / "eval-bridge" / "state" / "high_water_marks.json"
        state = json.loads(state_file.read_text()) if state_file.exists() else {}
        hw = json.loads(hw_file.read_text()) if hw_file.exists() else {}
        mode = state.get("agent_state", state.get("mode", "evolution"))
        cycle = state.get("cycle", 0)
        gen = state.get("generation", 0)
        paused = "PAUSED" if self.pause_requested else "RUNNING"

        print()
        print("  " + "-" * 54)
        print("  B.O.R.O.S  |  " + mode + "  |  c" + str(cycle) + "  |  g" + str(gen) + "  |  " + paused)

        if hw:
            scores_str = "  ".join(f"{k}:{v:.2f}" for k, v in sorted(hw.items())[:5] if isinstance(v, (int, float)))
            if scores_str:
                print("  Scores: " + scores_str)

        # Quick meta stats
        meta = self._get_meta_model()
        if meta:
            rates = meta.get_all_rates()
            best = max(rates.items(), key=lambda x: x[1], default=(None, 0))
            if best[0]:
                print("  Meta: " + best[0] + "=" + f"{best[1]:.2f}" + " (best)")

        # Quick vc stats
        vc = self._get_version_control()
        if vc:
            snaps = len(vc.index.get("snapshots", []))
            print("  Snapshots: " + str(snaps))

        print("  " + "-" * 54)
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
        if not self.cycles_log.exists() or self.cycles_log.stat().st_size == 0:
            print("  No logs")
            return
        try:
            lines = [l for l in self.cycles_log.read_text(encoding="utf-8").strip().split("\n") if l.strip()][-n:]
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
        print("  verbose " + ("on" if self.verbose else "off"))

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

    # ── New System Commands ──────────────────────────────────────────────────

    def _agents(self):
        """Show multi-agent system status."""
        print()
        print("  [Multi-Agent System]")
        print("  " + "-" * 54)

        try:
            from agents import ReflectorAgent, ArchitectAgent, ReviewerAgent, get_bus

            reflector = ReflectorAgent(self.kernel)
            architect = ArchitectAgent(self.kernel)
            reviewer = ReviewerAgent(self.kernel)

            rs = reflector.get_summary()
            print("  Reflector  | hypotheses=" + str(rs["total_hypotheses"]) + "  unacted=" + str(rs["unacted"]) + "  best_conf=" + f"{rs['best_confidence']:.2f}")

            arch_summary = architect.get_summary()
            print("  Architect  | proposals=" + str(arch_summary["total_proposals"]) + "  revisions=" + str(arch_summary["revision_count"]))

            rev_summary = reviewer.get_summary()
            print("  Reviewer   | rejections=" + str(rev_summary["total_rejections"]) + "  blocked=" + str(len(rev_summary["blocked_types"])))

            bus = get_bus()
            stats = bus.stats()
            handlers = sum(stats["handlers"].values())
            print()
            print("  AgentBus  | handlers=" + str(handlers) + "  queue=" + str(stats["queue_size"]) + "  running=" + str(stats["running"]).lower())

        except Exception as e:
            print("  [dim]Agents not available: " + str(e) + "[/dim]")
            print("  Run: pip install -e . to enable agents")

        print("  " + "-" * 54)
        print()

    def _world_model(self):
        """Show world model / capability graph status."""
        print()
        print("  [World Model v2 — Capability Graph]")
        print("  " + "-" * 54)

        try:
            wm_file = self.boros_root / "world_model.json"
            wm_data = json.loads(wm_file.read_text())

            graph = wm_data.get("capability_graph", {})
            print()
            print("  Capabilities (" + str(len(graph)) + "):")

            for name, info in sorted(graph.items()):
                tier = info.get("tier", 1)
                prereqs = info.get("prerequisites", [])
                prereq_str = ("prereq: " + ",".join(prereqs)) if prereqs else ""

                tier_symbols = {1: "I", 2: "II", 3: "III", 4: "IV"}
                print("    " + str(tier_symbols.get(tier, str(tier))).ljust(3) + " " + name.ljust(25) + " " + prereq_str)

            # Show milestones
            goals = wm_data.get("dynamic_goals", {})
            print()
            print("  Terminal: " + goals.get("terminal", ""))

            milestones = goals.get("milestones", [])
            for m in milestones:
                print("    > " + m.get("name", "") + "  —  " + m.get("criteria", ""))

            # Bounds
            bounds = wm_data.get("self_modification_bounds", {})
            can = bounds.get("can_change", [])
            cant = bounds.get("cannot_change", [])
            print()
            print("  Can evolve: " + ", ".join(can[:3]) + ("..." if len(can) > 3 else ""))
            print("  Cannot change: " + ", ".join(cant[:3]) + ("..." if len(cant) > 3 else ""))

        except Exception as e:
            print("  Error loading world model: " + str(e))

        print()
        print("  " + "-" * 54)
        print()

    def _metacog(self):
        """Show metacognition layer status."""
        print()
        print("  [Metacognition Layer]")
        print("  " + "-" * 54)

        try:
            from metacognition import MetacognitionLayer
            mc = MetacognitionLayer(self.boros_root)
            stats = mc.get_stats()

            print()
            print("  loops_detected  : " + str(stats["loop_count"]))
            print("  anomalies       : " + str(stats["anomalies_detected"]))
            print("  self_mods      : " + str(stats["self_modifications"]))
            print("  avg_coherence   : " + f"{stats['avg_coherence']:.3f}")

            # Check for interventions
            intervention = mc.suggest_intervention()
            if intervention:
                print()
                print("  ! " + intervention)

        except Exception as e:
            print("  Error: " + str(e))

        print()
        print("  " + "-" * 54)
        print()

    def _metalearn(self):
        """Show meta-learning model status."""
        print()
        print("  [Meta-Learning Model]")
        print("  " + "-" * 54)

        try:
            from meta_learning import MetaLearningModel, RLValidation

            meta = MetaLearningModel(self.boros_root)
            rates = meta.get_all_rates()

            print()
            print("  Change type success rates:")
            for ct, rate in rates.items():
                bar = "#" * int(rate * 10) + "-" * (10 - int(rate * 10))
                blocked = " [BLOCKED]" if meta.is_blocked(ct) else ""
                print("    " + ct.ljust(22) + " " + f"{rate:.3f}" + blocked + " [" + bar + "]")

            # Capability history
            cap_hist = meta.data.get("capability_history", {})
            if cap_hist:
                print()
                print("  Capability history:")
                for cap, hist in list(cap_hist.items())[:5]:
                    last_type = hist.get("last_change_type", "")
                    last_outcome = hist.get("last_outcome", "")
                    print("    " + cap.ljust(20) + " " + last_type.ljust(20) + " " + last_outcome)

            # RL validation sample
            rl = RLValidation(meta)
            eval_sample = rl.evaluate_proposal({
                "change_type": "additive_code",
                "capability": "reasoning",
                "target_file": "skills/reasoning/SKILL.md"
            })
            print()
            print("  RL eval sample (additive_code):")
            print("    action=" + eval_sample["action"] + "  expected_reward=" + f"{eval_sample['expected_reward']:.3f}" + "  risk=" + f"{eval_sample['risk']:.3f}")

        except Exception as e:
            print("  Error: " + str(e))

        print()
        print("  " + "-" * 54)
        print()

    def _version(self):
        """Show version control status."""
        print()
        print("  [Version Control]")
        print("  " + "-" * 54)

        try:
            from version_control import VersionControl

            vc = VersionControl(self.boros_root)
            logs = vc.log(limit=10)

            print()
            print("  Recent snapshots (" + str(len(logs)) + " recent):")
            for snap in logs:
                ts = snap.get("timestamp", "")[:19]
                label = snap.get("label", "")[:30]
                cycle = snap.get("cycle", 0)
                changed = len(snap.get("changed_files", []))
                print("    " + ts + "  c" + str(cycle) + "  " + label + "  (" + str(changed) + " files)")

            # Tags
            tags = vc.index.get("tags", {})
            if tags:
                print()
                print("  Tags:")
                for tag, snap_id in tags.items():
                    print("    " + tag + " -> " + snap_id[:25])

        except Exception as e:
            print("  Error: " + str(e))

        print()
        print("  " + "-" * 54)
        print()

    def _snapshot(self, args):
        """Create a snapshot."""
        label = args[0] if args else ""
        state_file = self.boros_root / "session" / "loop_state.json"
        cycle = 0
        if state_file.exists():
            try:
                cycle = json.loads(state_file.read_text()).get("cycle", 0)
            except Exception:
                pass

        try:
            from version_control import VersionControl
            vc = VersionControl(self.boros_root)
            snap_id = vc.snapshot(label=label, cycle=cycle)
            print("  Snapshot: " + snap_id)
        except Exception as e:
            print("  Error: " + str(e))

    def _diff(self, args):
        """Show diff between two snapshots."""
        if len(args) < 2:
            print("  Usage: diff <from_id> <to_id>")
            return

        try:
            from version_control import VersionControl
            vc = VersionControl(self.boros_root)
            result = vc.diff(args[0], args[1])

            if "error" in result:
                print("  " + result["error"])
                return

            print()
            for file, info in result.items():
                status = info.get("status", "")
                print("  " + status.upper().ljust(8) + " " + file)
            print()

        except Exception as e:
            print("  Error: " + str(e))

    def _rollback(self, args):
        """Rollback to a snapshot."""
        if not args:
            print("  Usage: rollback <snapshot_id>")
            return

        try:
            from version_control import VersionControl
            vc = VersionControl(self.boros_root)
            result = vc.rollback(args[0])

            if "error" in result:
                print("  " + result["error"])
            else:
                print("  Rolled back. Restored: " + ", ".join(result.get("restored", [])))

        except Exception as e:
            print("  Error: " + str(e))

    def _composition(self):
        """Show skill composition status."""
        print()
        print("  [Skill Composition]")
        print("  " + "-" * 54)

        try:
            from skills.skill_forge import SkillComposer, OperatorType

            composer = SkillComposer(self.kernel)

            print()
            print("  Operators:")
            for op in OperatorType:
                print("    " + op.value)

            # Show registered skills
            registered = list(composer._skill_registry.keys())
            print()
            print("  Registered skills: " + str(len(registered)))
            if registered:
                for name in registered[:10]:
                    print("    " + name)
                if len(registered) > 10:
                    print("    ... and " + str(len(registered) - 10) + " more")

        except Exception as e:
            print("  Error: " + str(e))

        print()
        print("  " + "-" * 54)
        print()

    def _perf(self):
        """Show performance metrics (APM-style)."""
        print()
        print("  [Performance]")
        print("  " + "-" * 54)

        # System metrics
        state_file = self.boros_root / "session" / "loop_state.json"
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
                cycle = state.get("cycle", 0)
                mode = state.get("agent_state", "unknown")

                # Calculate cycles per hour (approximate)
                started = state.get("started_at", "")
                if started:
                    from datetime import datetime as dt
                    try:
                        start = dt.fromisoformat(started.replace("Z", "+00:00"))
                        elapsed = (dt.utcnow() - start.replace(tzinfo=None)).total_seconds() / 3600
                        cph = cycle / max(0.01, elapsed)
                        print()
                        print("  cycles_per_hour : " + f"{cph:.1f}")
                        print("  total_cycles   : " + str(cycle))
                    except Exception:
                        pass

                print("  mode            : " + mode)
            except Exception:
                pass

        # Token usage
        hw_file = self.boros_root / "skills" / "eval-bridge" / "state" / "high_water_marks.json"
        if hw_file.exists():
            try:
                hw = json.loads(hw_file.read_text())
                total = sum(v for v in hw.values() if isinstance(v, (int, float)))
                print()
                print("  total_capabilities : " + str(len(hw)))
                print("  avg_score         : " + f"{total / max(1, len(hw)):.3f}")
            except Exception:
                pass

        # World model progress
        try:
            wm_file = self.boros_root / "world_model.json"
            if wm_file.exists():
                wm_data = json.loads(wm_file.read_text())
                caps = wm_data.get("capability_graph", {})
                print()
                print("  world_model_caps : " + str(len(caps)))
                print("  terminal_goal   : " + wm_data.get("dynamic_goals", {}).get("terminal", "")[:50])
        except Exception:
            pass

        print()
        print("  " + "-" * 54)
        print()

    def _help(self):
        print()
        print("  B.O.R.O.S Commands")
        print()
        print("  Core:")
        print("    s          status")
        print("    p          pause")
        print("    r          resume")
        print("  " + "-" * 54)
        print("  Lifecycle:")
        print("    e          evolve mode")
        print("    w          work mode")
        print("    fork       fork as agent")
        print("    rev        re-evolve")
        print("  " + "-" * 54)
        print("  Systems (Blueprint v2):")
        print("    ag         agents status")
        print("    wm         world model")
        print("    mc         metacognition")
        print("    ml         meta-learning")
        print("    vc         version control")
        print("    cp         skill composition")
        print("    perf       performance metrics")
        print("  " + "-" * 54)
        print("  Version Control:")
        print("    snap [label]  create snapshot")
        print("    diff <f> <t>  diff snapshots")
        print("    rollback <id> rollback")
        print("  " + "-" * 54)
        print("  Info:")
        print("    l [n]      logs (last n)")
        print("    sk         skills")
        print("    sc         scores")
        print("    v          toggle verbose")
        print("    h          help")
        print("    q          quit")
        print()

    # ── Kernel Loop ──────────────────────────────────────────────────────────

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

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_meta_model(self):
        try:
            from meta_learning import MetaLearningModel
            if self._meta_model is None:
                self._meta_model = MetaLearningModel(self.boros_root)
            return self._meta_model
        except Exception:
            return None

    def _get_version_control(self):
        try:
            from version_control import VersionControl
            if self._version_control is None:
                self._version_control = VersionControl(self.boros_root)
            return self._version_control
        except Exception:
            return None