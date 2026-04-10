"""
Boros Agent Loop - The core LLM <-> Tool dispatch engine.

This is the beating heart of Boros. It sends messages to the LLM,
parses tool_use responses, dispatches them through the kernel registry,
and loops until the LLM ends its turn or limits are reached.
"""

import importlib
import json
import platform
import random
import time
import traceback
from pathlib import Path


class AgentLoop:
    def __init__(self, kernel, log_callback=None):
        self.kernel = kernel
        self.log = log_callback or print
        self.max_tool_calls = kernel.config.get("max_tool_calls_per_cycle", 100)
        self.max_cycle_minutes = kernel.config.get("max_cycle_duration_minutes", 10)
        self.boros_root = kernel.boros_root

    # ────────────────────────────────────────────
    # System Prompt Construction
    # ────────────────────────────────────────────

    def build_system_prompt(self):
        """Load BOROS.md + live state + world model into the system prompt."""
        parts = []

        # 1. Primary instruction set
        boros_md = self.boros_root / "BOROS.md"
        if boros_md.exists():
            parts.append(boros_md.read_text(encoding="utf-8"))

        # 2. Current loop state
        state_file = self.boros_root / "session" / "loop_state.json"
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
                parts.append(f"## Current Loop State\n```json\n{json.dumps(state, indent=2)}\n```")
            except Exception:
                pass

        # 3. Dynamic World Model Injection (re-read every cycle for automatic alignment)
        wm_file = self.boros_root / "world_model.json"
        if wm_file.exists():
            try:
                wm = json.loads(wm_file.read_text())
                categories = wm.get("categories", {})
                if categories:
                    wm_lines = ["## World Model Categories (Your Evolution Targets)"]
                    wm_lines.append("These are the capabilities you MUST evolve toward. Every evolution cycle must target one of these.\n")
                    for cat_id, cat_data in categories.items():
                        name    = cat_data.get("name", cat_id)
                        desc    = cat_data.get("description", "")
                        related = cat_data.get("related_skills", [])
                        weight  = cat_data.get("weight", 1.0)

                        # Resolve active milestone (or fall back to flat fields)
                        milestones     = cat_data.get("milestones", [])
                        current_m_idx  = cat_data.get("current_milestone", 0)
                        if milestones and current_m_idx < len(milestones):
                            m       = milestones[current_m_idx]
                            anchors = m.get("anchors", cat_data.get("anchors", []))
                            rubric  = m.get("rubric",  cat_data.get("rubric", {}))
                            m_label = f" | Milestone {current_m_idx}: {m.get('name','?')} (difficulty={m.get('difficulty',5)}, unlock@{m.get('unlock_score',0.75)})"
                        else:
                            anchors = cat_data.get("anchors", [])
                            rubric  = cat_data.get("rubric", {})
                            m_label = ""

                        wm_lines.append(f"### {name} (`{cat_id}`, weight={weight}{m_label})")
                        wm_lines.append(f"{desc}\n")
                        if related:
                            wm_lines.append(f"**Related skills to evolve**: {', '.join(related)}")
                        if anchors:
                            wm_lines.append(f"**Current milestone anchors**: {'; '.join(anchors[:3])}")
                        if rubric.get("level_4"):
                            wm_lines.append(f"**Level 4 Target**: {rubric['level_4']}")
                        wm_lines.append("")
                    parts.append("\n".join(wm_lines))
            except Exception:
                pass

        # 4. Recent scores
        score_dir = self.boros_root / "evals" / "scores"
        if score_dir.exists():
            score_files = sorted(score_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:3]
            if score_files:
                scores_text = []
                for sf in score_files:
                    try:
                        scores_text.append(json.loads(sf.read_text()))
                    except Exception:
                        pass
                if scores_text:
                    parts.append(f"## Recent Evaluation Scores\n```json\n{json.dumps(scores_text, indent=2)}\n```")

        # 5. Score history (last 5 entries)
        score_hist = self.boros_root / "memory" / "score_history.jsonl"
        has_scores = False
        if score_hist.exists():
            try:
                raw = score_hist.read_text().strip()
                if raw:
                    has_scores = True
                    lines = raw.split("\n")
                    recent = lines[-5:] if len(lines) > 5 else lines
                    entries = [json.loads(l) for l in recent if l.strip()]
                    if entries:
                        parts.append(f"## Score History (last {len(entries)} entries)\n```json\n{json.dumps(entries, indent=2)}\n```")
            except Exception:
                pass

        # 5. Past hypothesis outcomes — DO NOT REPEAT FAILED APPROACHES
        hyp_records_dir = self.boros_root / "memory" / "evolution_records"
        if hyp_records_dir.exists():
            try:
                hyp_files = sorted(
                    hyp_records_dir.glob("hyp-cycle*.json"),
                    key=lambda f: f.stat().st_mtime
                )[-10:]
                if hyp_files:
                    hyp_lines = ["## Previous Evolution Attempts (DO NOT REPEAT FAILED APPROACHES)"]
                    hyp_lines.append("Study these outcomes before writing your hypothesis. Never repeat an approach that regressed or was neutral.\n")
                    for hf in hyp_files:
                        try:
                            h = json.loads(hf.read_text())
                            cycle_n   = h.get("cycle", "?")
                            target    = h.get("target_skill", "?")
                            rationale = h.get("rationale", "")[:120]
                            outcome   = h.get("actual_outcome", "unknown").upper()
                            before    = h.get("score_before", {})
                            after     = h.get("score_after", {})
                            score_str = ""
                            if before and after:
                                for cat in set(list(before.keys()) + list(after.keys())):
                                    b = before.get(cat, "?")
                                    a = after.get(cat, "?")
                                    score_str += f" {cat}: {b}→{a}"
                            hyp_lines.append(f"- Cycle {cycle_n} | {target} | {outcome} |{score_str}")
                            hyp_lines.append(f"  Rationale: {rationale}")
                        except Exception:
                            pass
                    parts.append("\n".join(hyp_lines))
            except Exception:
                pass

        # 6. Surface regression warnings
        try:
            ledger = importlib.import_module("boros.skills.meta-evolution.functions._internal.evolution_ledger")
            
            regressions = ledger.query_ledger(str(self.boros_root), outcome="regressed", limit=10)
            if regressions:
                reg_lines = ["## REGRESSION WARNINGS — DO NOT REPEAT THESE"]
                for r in regressions:
                    delta = r.get('delta')
                    delta_str = f"{delta:+.3f}" if isinstance(delta, (int, float)) else "unknown"
                    appr = str(r.get('approach', ''))[:80].replace('\n', ' ')
                    reg_lines.append(f"- Cycle {r.get('cycle')}: Changed {r.get('target_file')} "
                                     f"({appr}...) → REGRESSED {delta_str}")
                parts.append("\n".join(reg_lines))

            blocked = []
            for r in ledger.query_ledger(str(self.boros_root), limit=50):
                if r.get("outcome") in ("regressed", "neutral"):
                    tf = r.get("target_file")
                    if tf: blocked.append(tf)
            if blocked:
                b_lines = ["## BLOCKED FILES (recently failed, try different approach)"]
                for f in set(blocked):
                    b_lines.append(f"- {f}")
                parts.append("\n".join(b_lines))
        except Exception:
            pass

        # 7. Active hypothesis
        hyp_file = self.boros_root / "session" / "hypothesis.json"
        if hyp_file.exists():
            try:
                parts.append(f"## Active Task Binding\nYou must operate strictly on this task until completed.\n```json\n{hyp_file.read_text()}\n```")
            except Exception:
                pass

        # 8. High-water marks
        hw_file = self.boros_root / "skills" / "eval-bridge" / "state" / "high_water_marks.json"
        if hw_file.exists():
            try:
                parts.append(f"## High-Water Marks\n```json\n{hw_file.read_text()}\n```")
            except Exception:
                pass

        # 9. Bootstrap mode — if no scores exist, force immediate eval
        if not has_scores:
            parts.append(
                "## ⚡ BOOTSTRAP MODE — CRITICAL INSTRUCTION\n"
                "You have ZERO evaluation scores. The evolution loop cannot target improvements without data.\n\n"
                "**You MUST follow this exact sequence:**\n"
                "1. `loop_start` → initialize cycle\n"
                "2. `eval_request` → submit evaluation for ALL world model categories (pass cycle number)\n"
                "3. `eval_read_scores` → pass the `request_id` from step 2 to get results (this will wait)\n"
                "4. `loop_end_cycle` → finalize\n\n"
                "**DO NOT attempt to evolve code until you have baseline scores.**\n"
                "**DO NOT target eval-bridge. DO NOT write hypotheses. Just get scores first.**"
            )

        # 10. Environment reminder
        os_name = platform.system()
        if os_name == "Windows":
            env_note = (
                "## Environment\n"
                "- OS: Windows. Use `dir` to list directories, `type` to read files.\n"
                "- Do NOT use `ls` or `cat` — they will fail.\n"
                "- Use backslashes in terminal paths: `type skills\\memory\\functions\\memory_page_in.py`\n"
                "- CWD is the boros root. Do NOT prefix paths with `boros/`."
            )
        else:
            env_note = (
                "## Environment\n"
                f"- OS: {os_name}. Use `ls` to list directories, `cat` to read files.\n"
                "- Use forward slashes in paths: `cat skills/memory/functions/memory_page_in.py`\n"
                "- CWD is the boros root. Do NOT prefix paths with `boros/`."
            )
        parts.append(env_note)

        return "\n\n---\n\n".join(parts)

    # ────────────────────────────────────────────
    # Tool Manifest
    # ────────────────────────────────────────────

    def build_tools(self):
        """Build tool list from schemas, filtered to registered functions."""
        from boros.tool_schemas import TOOL_SCHEMAS
        tools = []
        for func_name in self.kernel.registry:
            if func_name in TOOL_SCHEMAS:
                tools.append(TOOL_SCHEMAS[func_name])
        return tools

    # ────────────────────────────────────────────
    # Tool Dispatch
    # ────────────────────────────────────────────

    def _describe_tool_call(self, name, inp):
        """Return a short human-readable sentence describing what this tool call is doing."""
        def _t(text, limit=70):
            return text[:limit] + ("…" if len(text) > limit else "")

        table = {
            "loop_start":               lambda p: "Starting a new evolution cycle",
            "loop_advance_stage":       lambda p: f"Stage complete — moving to next stage",
            "loop_end_cycle":           lambda p: "Cycle done — saving high-water marks",
            "loop_get_state":           lambda p: "Checking current loop state",
            "eval_request":             lambda p: f"Submitting evaluation for: {', '.join(p.get('categories', ['all categories']))}",
            "eval_read_scores":         lambda p: "Waiting for evaluation results…" if p.get("eval_id") else "Reading latest scores",
            "eval_check_regression":    lambda p: "Checking if this change improved or hurt the score",
            "eval_update_high_water":   lambda p: "Updating personal-best score records",
            "eval_backfill":            lambda p: "Backfilling historical scores",
            "reflection_analyze_trace": lambda p: "Analyzing score history to find the weakest capability",
            "reflection_write_hypothesis": lambda p: f"Hypothesis: {_t(p.get('rationale', '?'))}",
            "reflection_read_hypothesis":  lambda p: "Reading the active hypothesis",
            "evolve_orient":            lambda p: "Finding which skill to target based on current scores",
            "evolve_set_target":        lambda p: f"Targeting '{p.get('target', '?')}' skill for improvement",
            "evolve_propose":           lambda p: f"Packaging change into a proposal: {_t(p.get('description', '?'))}",
            "evolve_apply":             lambda p: f"Applying approved proposal and hot-reloading",
            "evolve_rollback":          lambda p: f"Rolling back '{p.get('target', '?')}' — score regressed",
            "evolve_history":           lambda p: "Reading past evolution attempts",
            "evolve_modify_loop":       lambda p: f"Proposing loop change: {_t(p.get('modification', '?'))}",
            "evolve_create_skill":      lambda p: f"Creating a new skill: {p.get('skill_name', '?')}",
            "forge_snapshot":           lambda p: f"Snapshotting '{p.get('target', '?')}' in case rollback is needed",
            "forge_read_skill_md":      lambda p: f"Reading '{p.get('skill_name', '?')}' skill definition",
            "forge_edit_skill_md":      lambda p: f"Editing '{p.get('skill_name', '?')}' instructions (section: {p.get('section_name', p.get('section', '?'))})",
            "forge_validate":           lambda p: f"Checking syntax of '{p.get('target', p.get('skill_name', '?'))}'",
            "forge_test_suite":         lambda p: f"Running tests on '{p.get('skill_name', '?')}'",
            "forge_apply_diff":         lambda p: f"Applying patch to: {p.get('target_file', '?')}",
            "forge_rollback":           lambda p: f"Restoring snapshot for '{p.get('target', '?')}'",
            "forge_create_skill":       lambda p: f"Scaffolding new skill: {p.get('skill_name', '?')}",
            "forge_invoke":             lambda p: f"Testing function: {p.get('function_name', '?')}",
            "review_proposal":          lambda p: "Sending proposal to independent review board for approval",
            "review_history":           lambda p: "Reading past review decisions",
            "review_criteria_update":   lambda p: "Updating review board criteria",
            "tool_file_edit_diff":      lambda p: f"Patching: {p.get('target_file', '?')}",
            "tool_file_write":          lambda p: f"Creating: {p.get('path', '?')}",
            "tool_terminal":            lambda p: f"Running: {_t(str(p.get('command', '?')), 60)}",
            "tool_terminal_input":      lambda p: "Sending input to terminal process",
            "tool_terminal_kill":       lambda p: "Stopping background terminal process",
            "tool_apply_patch":         lambda p: f"Applying patch to: {p.get('target_file', '?')}",
            "reason_decompose":         lambda p: f"Breaking down: {_t(p.get('problem', '?'))}",
            "reason_evaluate_options":  lambda p: "Scoring candidate approaches against criteria",
            "reason_check_logic":       lambda p: "Checking the hypothesis for logical gaps",
            "reason_generate_plan":     lambda p: "Generating a step-by-step execution plan",
            "memory_page_in":           lambda p: f"Loading memory: {p.get('source', 'scores')}",
            "memory_page_out":          lambda p: "Saving data to memory",
            "memory_commit_archival":   lambda p: "Recording this cycle's outcome to long-term memory",
            "memory_search_sql":        lambda p: f"Searching memory: {_t(p.get('query', '?'))}",
            "research_search_engine":   lambda p: f"Searching the web for: \"{_t(p.get('query', '?'))}\"",
            "research_browse":          lambda p: f"Reading: {_t(p.get('url', '?'), 60)}",
            "research_archive_source":  lambda p: f"Archiving source: {_t(p.get('url', '?'), 60)}",
            "context_load":             lambda p: "Loading active context into memory",
            "context_get_manifest":     lambda p: "Reading the context manifest",
            "router_get_tools":         lambda p: "Getting available tools for this stage",
            "router_get_budget":        lambda p: "Checking token/call budget",
            "router_manifest":          lambda p: "Reading the skill manifest",
            "mode_get":                 lambda p: "Reading current operating mode",
            "mode_set":                 lambda p: f"Switching mode to: {p.get('mode', '?')}",
            "generate_evaluation_artifact": lambda p: f"Writing eval artifact: {p.get('artifact_name', '?')}",
        }

        fn = table.get(name)
        if fn is None:
            return None
        try:
            return fn(inp)
        except Exception:
            return None

    def dispatch_tool(self, name, params):
        """Dispatch a tool call to the kernel registry."""
        if name not in self.kernel.registry:
            return {"status": "error", "message": f"Unknown tool: {name}"}
        try:
            result = self.kernel.registry[name](params or {}, self.kernel)
            return result
        except Exception as e:
            tb = traceback.format_exc()
            self.log(f"[ERROR] Tool {name} crashed: {e}")
            return {"status": "error", "message": str(e), "traceback": tb}

    # ────────────────────────────────────────────
    # Single Cycle
    # ────────────────────────────────────────────

    def run_evolution_cycle(self):
        # Sync world model state so live edits to world_model.json are picked up
        try:
            self.kernel._sync_world_model_state(self.boros_root)
        except Exception:
            pass

        system = self.build_system_prompt()
        tools = self.build_tools()

        messages = [{"role": "user", "content": self._cycle_prompt()}]

        tool_call_count = 0
        cycle_start = time.time()
        token_budget = self.kernel.config.get("max_tokens_per_cycle", 500000)
        tokens_used = 0

        self.log("[CYCLE] Starting evolution cycle...")
        status = "completed"
        empty_turns = 0

        try:
            executed_tools = set()
            while tool_call_count < self.max_tool_calls:
                # Time limit check
                elapsed_min = (time.time() - cycle_start) / 60
                if elapsed_min > self.max_cycle_minutes:
                    self.log(f"[CYCLE] Time limit ({self.max_cycle_minutes}m) reached.")
                    status = "timeout"
                    self._ensure_cycle_committed()
                    break

                # Call LLM
                try:
                    response = self.kernel.evolution_llm.complete(messages, tools, system)
                except Exception as e:
                    self.log(f"[ERROR] LLM call failed: {e}")
                    self.log(traceback.format_exc())
                    status = "error"
                    raise  # Let the continuous loop catch this and trigger the cooldown sleep

                content = response.get("content", [])
                stop_reason = response.get("stop_reason", "end_turn")
                usage = response.get("usage", {})

                # Log text output
                for block in content:
                    if block.get("type") == "text" and block.get("text"):
                        self.log(f"[BOROS] {block['text'][:800]}")

                # Track tokens and enforce budget
                if usage:
                    in_tok = usage.get('input_tokens', 0)
                    out_tok = usage.get('output_tokens', 0)
                    tokens_used += (in_tok + out_tok)
                    self.log(f"[TOKENS] in={in_tok} out={out_tok} | total={tokens_used}/{token_budget}")

                if tokens_used > token_budget:
                    self.log(f"[CYCLE] Token budget ({token_budget}) exceeded. Soft-terminating cycle.")
                    status = "budget_exceeded"
                    self._ensure_cycle_committed()
                    break

                # Append assistant response
                messages.append({"role": "assistant", "content": content})

                # Natural stop
                if stop_reason == "end_turn":
                    self.log("[CYCLE] LLM ended turn naturally.")
                    self._ensure_cycle_committed()
                    break

                # Dispatch tool calls
                tool_results = []
                for block in content:
                    if block.get("type") == "tool_use":
                        name = block["name"]
                        inp = block.get("input", {})
                        tid = block["id"]
                        
                        # Deduplicate identical non-polling tool calls
                        sig = (name, json.dumps(inp, sort_keys=True))
                        is_polling = name in ("eval_read_scores", "tool_terminal_input", "router_get_budget")
                        is_duplicate = (sig in executed_tools) and not is_polling
                        
                        if is_duplicate:
                            self.log(f"[STATUS] ⚠️ Blocked duplicate tool call: {name}")
                            result = {"status": "error", "message": "Duplicate tool call detected. You already executed this exact command this cycle. Try something else to avoid looping."}
                            result_str = json.dumps(result)
                            tool_results.append({"type": "tool_result", "tool_use_id": tid, "content": result_str})
                            continue

                        if not is_polling:
                            executed_tools.add(sig)

                        _tool_desc = self._describe_tool_call(name, inp)
                        if _tool_desc:
                            self.log(f"[STATUS] {_tool_desc}")

                        if name == "evolve_propose":
                            desc = inp.get("description", "")
                            self.log(f"\n========================================")
                            self.log(f"📝 [PROPOSAL CREATED]: {desc}")
                            self.log(f"========================================\n")
                            self.log(f"[TOOL] → {name}({json.dumps(inp, default=str)[:300]})")
                        elif name == "tool_file_edit_diff":
                            self.log(f"\n========================================")
                            self.log(f"⚙️ [CODE MUTATION] Targeting: {inp.get('target_file')}")
                            for i, chunk in enumerate(inp.get("replacement_chunks", [])):
                                self.log(f"\n--- Chunk {i+1} ---")
                                target_lines = chunk.get("target_content", "").split("\n")
                                replace_lines = chunk.get("replacement_content", "").split("\n")
                                for line in target_lines: self.log(f"[-] {line}")
                                for line in replace_lines: self.log(f"[+] {line}")
                            self.log(f"========================================\n")
                            self.log(f"[TOOL] → {name}(...)")
                        else:
                            self.log(f"[TOOL] → {name}({json.dumps(inp, default=str)[:300]})")

                        result = self.dispatch_tool(name, inp)
                        result_str = json.dumps(result, default=str)

                        if name in ("evolve_propose", "tool_file_edit_diff"):
                            self.log(f"[TOOL] ← {result_str}") # print full result for these
                        else:
                            self.log(f"[TOOL] ← {result_str[:400]}")

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tid,
                            "content": result_str
                        })
                        tool_call_count += 1

                if not tool_results:
                    empty_turns += 1
                    if empty_turns >= 3:
                        self.log("[CYCLE] No tool calls despite warnings. Ending.")
                        self._ensure_cycle_committed()
                        break
                    else:
                        self.log(f"[CYCLE] Enforcing action (warning {empty_turns}/3)")
                        messages.append({
                            "role": "user",
                            "content": "SYSTEM NOTIFICATION: No tool calls detected. You MUST execute at least one tool per cycle to advance the active task. Empty cycles are not permitted."
                        })
                        continue
                else:
                    empty_turns = 0

                messages.append({"role": "user", "content": tool_results})

        finally:
            # Log cycle end to file
            log_file = self.boros_root / "logs" / "cycles.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, "a") as f:
                f.write(f"Cycle ended. status={status} tool_calls={tool_call_count}\n")
                f.flush()

        self.log(f"[CYCLE] Finished. {tool_call_count} tool calls.")
        return tool_call_count

    def _ensure_cycle_committed(self):
        """Safety net: if the LLM ends its turn without calling loop_end_cycle,
        call it automatically so high-water marks and state are always persisted."""
        state_file = self.boros_root / "session" / "loop_state.json"
        try:
            if not state_file.exists():
                return
            state = json.loads(state_file.read_text())
            stage = state.get("stage")
            # If stage is still active (not None/END), the LLM skipped COMMIT
            if stage and stage not in (None, "END"):
                self.log(f"[CYCLE] Safety net: LLM ended without calling loop_end_cycle (stage={stage}). Auto-committing.")
                if "loop_end_cycle" in self.kernel.registry:
                    result = self.kernel.registry["loop_end_cycle"]({}, self.kernel)
                    hw = result.get("high_water_updated", {})
                    if hw:
                        self.log(f"[CYCLE] High-water marks updated: {hw}")
                else:
                    self.log("[CYCLE] WARNING: loop_end_cycle not in registry — high-water marks not updated.")
        except Exception as e:
            self.log(f"[CYCLE] _ensure_cycle_committed failed: {e}")

    def run_execution_cycle(self, active_task=None):
        """Run one full execution cycle (acting as a digital employee)."""
        system = self.build_system_prompt()
        tools = self.build_tools()
        messages = [{"role": "user", "content": self._execution_prompt(active_task)}]
        tool_call_count = 0
        cycle_start = time.time()
        token_budget = self.kernel.config.get("max_tokens_per_cycle", 500000)
        tokens_used = 0
        
        self.log("[CYCLE] Starting execution cycle...")
        status = "completed"
        empty_turns = 0

        try:
            while tool_call_count < self.max_tool_calls:
                # Time limit check
                if (time.time() - cycle_start) / 60 > self.max_cycle_minutes:
                    self.log(f"[CYCLE] Time limit ({self.max_cycle_minutes}m) reached.")
                    status = "timeout"
                    break

                try:
                    response = self.kernel.evolution_llm.complete(messages, tools, system)
                except Exception as e:
                    self.log(f"[ERROR] LLM call failed: {e}")
                    status = "error"
                    raise

                content = response.get("content", [])
                stop_reason = response.get("stop_reason", "end_turn")

                for block in content:
                    if block.get("type") == "text" and block.get("text"):
                        self.log(f"[BOROS EXECUTION] {block['text'][:800]}")

                usage = response.get("usage", {})
                if usage:
                    tokens_used += usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
                    self.log(f"[TOKENS] total={tokens_used}/{token_budget}")
                
                if tokens_used > token_budget:
                    self.log(f"[CYCLE] Token budget ({token_budget}) exceeded. Terminating.")
                    status = "budget_exceeded"
                    break

                messages.append({"role": "assistant", "content": content})

                if stop_reason == "end_turn":
                    break

                tool_results = []
                for block in content:
                    if block.get("type") == "tool_use":
                        name = block["name"]
                        inp = block.get("input", {})
                        tid = block["id"]
                        self.log(f"[EXEC TOOL] → {name}(...)")
                        result = self.dispatch_tool(name, inp)
                        result_str = json.dumps(result, default=str)
                        self.log(f"[EXEC TOOL] ← {result_str[:400]}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tid,
                            "content": result_str
                        })
                        tool_call_count += 1

                if not tool_results:
                    empty_turns += 1
                    if empty_turns >= 3:
                        self.log("[CYCLE] No tool calls despite warnings. Ending.")
                        break
                    else:
                        self.log(f"[CYCLE] Enforcing action (warning {empty_turns}/3)")
                        messages.append({
                            "role": "user",
                            "content": "SYSTEM NOTIFICATION: No tool calls detected. You MUST execute at least one tool per cycle to advance the active task. Empty cycles are not permitted."
                        })
                        continue
                else:
                    empty_turns = 0

                messages.append({"role": "user", "content": tool_results})
        finally:
            log_file = self.boros_root / "logs" / "execution_cycles.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, "a") as f:
                f.write(f"Execution cycle ended. status={status} tool_calls={tool_call_count}\n")

        self.log(f"[CYCLE] Execution Finished. {tool_call_count} tool calls.")
        return tool_call_count

    # ────────────────────────────────────────────
    # Continuous Loop
    # ────────────────────────────────────────────

    def run_continuous(self, should_pause=None, on_cycle_complete=None):
        """Run evolution cycles until paused."""
        cycle_num = 0
        fail_count = 0
        while True:
            if should_pause and should_pause():
                self.log("[LOOP] Pause requested.")
                break

            cycle_num += 1

            mode = "evolution"
            state_file = self.boros_root / "session" / "loop_state.json"
            if state_file.exists():
                try:
                    mode = json.loads(state_file.read_text()).get("mode", "evolution")
                except:
                    pass

            try:
                if mode == "evolution":
                    self.log(f"\n{'='*60}")
                    self.log(f"  {mode.upper()} CYCLE {cycle_num}")
                    self.log(f"{'='*60}\n")
                    tc = self.run_evolution_cycle()
                else:
                    pending_file = self.boros_root / "commands" / "pending.json"
                    has_tasks = False
                    task_text = None
                    if pending_file.exists():
                        try:
                            data = json.loads(pending_file.read_text())
                            if data.get("pending"):
                                has_tasks = True
                                task_text = data["pending"].pop(0)
                                pending_file.write_text(json.dumps(data, indent=2))
                        except Exception: pass

                    if not has_tasks:
                        if not getattr(self, "_was_idling", False):
                            self.log("[BOROS] Idling in Employee Mode, waiting for tasks...")
                            self._was_idling = True
                        time.sleep(2)
                        continue

                    self._was_idling = False
                    self.log(f"\n{'='*60}")
                    self.log(f"  {mode.upper()} CYCLE {cycle_num}")
                    self.log(f"{'='*60}\n")
                    tc = self.run_execution_cycle(active_task=task_text)
                    time.sleep(1) # Prevent spin-locking if tasks finish very fast

                if on_cycle_complete:
                    on_cycle_complete(cycle_num, tc)
                fail_count = 0  # Reset backoff on success
            except Exception as e:
                self.log(f"[ERROR] Cycle {cycle_num} failed: {e}")
                self.log(traceback.format_exc())
                fail_count += 1
                wait_time = min(300, 30 * (2 ** (fail_count - 1)))
                jitter = random.uniform(0, 5)
                total_wait = wait_time + jitter
                self.log(f"[RATE_LIMIT] API limit hit. Exponential backoff for {total_wait:.1f}s (Fail #{fail_count})")
                time.sleep(total_wait)

    # ────────────────────────────────────────────
    # Cycle Prompts
    # ────────────────────────────────────────────

    def _execution_prompt(self, active_task=None):
        task_str = active_task if active_task else "Check for any active objectives and execute them."
        return (
            "You are Boros in EXECUTION MODE.\n"
            "You are an unconstrained, super reliable digital employee.\n"
            f"Your immediate priority is to complete this specific task for the user:\n\n{task_str}\n\n"
            "Use your tools to solve it, and naturally end your turn when finished.\n"
            "Do NOT attempt to evolve the codebase or meta-evaluate in this mode."
        )

    def _cycle_prompt(self):
        prompt_path = self.boros_root / "cycle_prompt.md"
        if prompt_path.exists():
            try:
                return prompt_path.read_text(encoding="utf-8")
            except Exception:
                pass
        # Fallback if file is missing
        return (
            "You are Boros — an autonomous, self-evolving AI substrate.\n"
            "Begin a new evolution cycle: REFLECT → EVOLVE → EVAL.\n"
            "Use loop_start, eval_read_scores, reflection_analyze_trace, "
            "then evolve and evaluate. Write REAL code."
        )
