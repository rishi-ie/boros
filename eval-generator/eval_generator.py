import os, sys, time, json, uuid, datetime, shutil
import random
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

boros_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adapters import load_adapter
from kernel import BorosKernel
from tool_schemas import TOOL_SCHEMAS
from tool_dispatcher import ToolDispatcher

# ─────────────────────────────────────────────────────────────
# Logging helper
# ─────────────────────────────────────────────────────────────
def _log(msg, level="INFO"):
    ts = datetime.datetime.now(datetime.UTC).strftime("%H:%M:%S")
    prefix = {"INFO": "ℹ", "OK": "✔", "WARN": "⚠", "ERR": "✗", "START": "►", "END": "■"}.get(level, "·")
    line = f"[{ts}] {prefix}  {msg}"
    print(line, flush=True)
    return line


class EvalGenerator:
    def __init__(self):
        self.base_dir = os.path.dirname(__file__)
        self.shared_dir = os.path.join(self.base_dir, "shared")
        self.requests_dir = os.path.join(self.shared_dir, "requests")
        self.results_dir = os.path.join(self.shared_dir, "results")
        self.sandboxes_dir = os.path.join(self.base_dir, "sandboxes")
        self.generated_tests_dir = os.path.join(self.base_dir, "generated-tests")
        self.logs_dir = os.path.join(self.base_dir, "logs")
        self.scoring_dir = os.path.join(self.base_dir, "scoring")
        self.world_model_path = os.path.join(boros_root, "world_model.json")
        self.config_path = os.path.join(boros_root, "config.json")

        for d in [self.requests_dir, self.results_dir, self.sandboxes_dir,
                  self.generated_tests_dir, self.logs_dir, self.scoring_dir]:
            os.makedirs(d, exist_ok=True)

        with open(self.config_path) as f:
            self.config = json.load(f)

        # Eval-specific config
        self.max_concurrency = self.config.get("eval_concurrency", 2)
        self.category_timeout = self.config.get("eval_category_timeout_seconds", 90)
        self.max_agent_iterations = self.config.get("eval_max_agent_iterations", 3)
        self.request_expiry_minutes = self.config.get("eval_request_expiry_minutes", 15)

        try:
            self.llm = load_adapter(self.config["providers"]["meta_eval_api"])
            self.actor_llm = load_adapter(self.config["providers"]["evolution_api"])
            _log("LLM adapters loaded successfully", "OK")
        except Exception as e:
            _log(f"Could not load LLM adapter: {e}", "ERR")
            self.llm = None
            self.actor_llm = None

        with open(self.world_model_path) as f:
            self.world_model = json.load(f)

        _log(f"World model loaded: {len(self.world_model.get('categories', {}))} categories", "OK")
        _log(f"Config: concurrency={self.max_concurrency}, timeout={self.category_timeout}s, iterations={self.max_agent_iterations}", "OK")

        self._write_ready_file()

    def _write_ready_file(self):
        with open(os.path.join(self.shared_dir, ".ready"), "w") as f:
            f.write("ready")

    def run(self):
        _log("Eval Generator listening for requests...", "START")
        _log(f"  Requests dir: {self.requests_dir}")
        _log(f"  Results dir:  {self.results_dir}")
        while True:
            self._poll_requests()
            time.sleep(2)

    # ─────────────────────────────────────────────────────────
    # Request polling & expiry
    # ─────────────────────────────────────────────────────────
    def _poll_requests(self):
        self._write_ready_file()  # FIX-18: Update heartbeat timestamp
        if not os.path.isdir(self.requests_dir):
            return
        for req_file in os.listdir(self.requests_dir):
            if req_file.endswith(".json"):
                req_path = os.path.join(self.requests_dir, req_file)
                # Check for stale requests
                try:
                    file_age_seconds = time.time() - os.path.getmtime(req_path)
                    if file_age_seconds > self.request_expiry_minutes * 60:
                        _log(f"Expiring stale request {req_file} (age: {file_age_seconds/60:.0f}min)", "WARN")
                        os.remove(req_path)
                        continue
                except Exception:
                    pass
                self._process_request(req_path)

    # ─────────────────────────────────────────────────────────
    # Milestone helpers
    # ─────────────────────────────────────────────────────────
    def _get_milestone_data(self, category_id):
        """Return the active milestone data for a category, falling back to flat fields."""
        cat = self.world_model["categories"].get(category_id, {})
        milestones = cat.get("milestones", [])
        current_idx = cat.get("current_milestone", 0)
        if milestones and current_idx < len(milestones):
            m = milestones[current_idx]
            return {
                "anchors":         m.get("anchors",         cat.get("anchors", [])),
                "rubric":          m.get("rubric",          cat.get("rubric", {})),
                "failure_modes":   m.get("failure_modes",   cat.get("failure_modes", [])),
                "task_template":   m.get("task_template",   cat.get("task_template", "")),
                "execution_pattern": m.get("execution_pattern", cat.get("execution_pattern", {})),
                "difficulty":      m.get("difficulty",      5),
                "milestone_level": current_idx,
                "milestone_name":  m.get("name", f"Level {current_idx}")
            }
        # Flat fallback — no milestones array or index out of range
        return {
            "anchors":           cat.get("anchors", []),
            "rubric":            cat.get("rubric", {}),
            "failure_modes":     cat.get("failure_modes", []),
            "task_template":     cat.get("task_template", ""),
            "execution_pattern": cat.get("execution_pattern", {}),
            "difficulty":        5,
            "milestone_level":   0,
            "milestone_name":    "default"
        }

    # ─────────────────────────────────────────────────────────
    # Task generation
    # ─────────────────────────────────────────────────────────
    def _generate_task(self, category_id):
        cat = self.world_model["categories"].get(category_id)
        if not cat or not self.llm:
            return "Write a script that prints Hello World to output.txt."

        md = self._get_milestone_data(category_id)
        anchors       = md["anchors"]
        rubric_l4     = md["rubric"].get("level_4", "Excellent performance")
        exec_pattern  = md["execution_pattern"]
        failure_modes = md["failure_modes"]
        task_template = md["task_template"]

        anchor  = random.choice(anchors)       if anchors       else "general capability"
        failure = random.choice(failure_modes) if failure_modes else "generic failure"

        template_instruction = (
            f"\n\nCRITICAL: The task you generate MUST require the agent to follow this behavioral pattern:\n"
            f"{task_template}\n"
            f"Design the scenario so that skipping these steps makes the task impossible to complete correctly."
        ) if task_template else ""

        prompt = (
            f"Create a concrete, verifiable task that tests the '{category_id}' capability "
            f"at milestone level {md['milestone_level']} ({md['milestone_name']}).\n\n"
            f"The task must specifically test this anchor criterion: '{anchor}'\n"
            f"The gold standard (Level 4) is: '{rubric_l4}'\n"
            f"Design the task to expose this failure mode: '{failure}'\n\n"
            f"Execution pattern the agent should follow:\n"
            + "\n".join(f"  {k}: {v}" for k, v in exec_pattern.items())
            + template_instruction + "\n\n"
            f"The task must be verifiable by checking file outputs in a sandbox. "
            f"Output just the task prompt, nothing else."
        )
        try:
            res = self.llm.complete(
                [{"role": "user", "content": prompt}],
                system="You generate targeted evaluation tasks. Output only the task prompt."
            )
            text = "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text")
            return text.strip() or "Write a python script to output.txt"
        except Exception as e:
            _log(f"  Task generation failed: {e}", "WARN")
            return "Write a python script to output.txt that adds two numbers."

    # ─────────────────────────────────────────────────────────
    # Grading
    # ─────────────────────────────────────────────────────────
    def _grade_sandbox(self, transcript, category_id, workspace_dir):
        # ── Layer 1: Objective deterministic checks ───────────────
        file_list = []
        if workspace_dir and os.path.exists(workspace_dir):
            file_list = [f for f in os.listdir(workspace_dir)
                         if os.path.isfile(os.path.join(workspace_dir, f))]
        files_str = f"Files created: {', '.join(file_list)}" if file_list else "No files created."

        no_files = len(file_list) == 0

        # Hard fail only if the agent produced nothing AND the final action was an error.
        # Intermediate "Error:" lines are recoverable — we don't penalise recovery.
        lines = [l.strip() for l in transcript.splitlines() if l.strip()]
        last_tool_line = next((l for l in reversed(lines) if l.startswith("Tool ")), "")
        fatal_final_error = ("Error:" in last_tool_line or '"status": "error"' in last_tool_line)

        if no_files and fatal_final_error:
            reason = "Task failed: no output files produced and final tool call errored."
            return {"outcome_score": 0.0, "quality_score": 0.0, "quality_reason": reason, "outcome_details": files_str}

        # ── Layer 2: Outcome score — deterministic artifact checks ──
        outcome_score = 0.0
        structural_notes = []

        # +0.5: at least one output file with meaningful content (>50 bytes)
        meaningful_files = 0
        for fname in file_list:
            fpath = os.path.join(workspace_dir, fname)
            try:
                if os.path.getsize(fpath) > 50:
                    meaningful_files += 1
            except OSError:
                pass
        if meaningful_files > 0:
            outcome_score += 0.5
            structural_notes.append(f"{meaningful_files} meaningful output file(s)")

        # +0.25: agent made domain-relevant tool calls (not just terminal spam)
        domain_tools = ["research_search_engine", "research_browse", "reason_decompose",
                        "reason_evaluate_options", "reason_check_logic", "reason_generate_plan",
                        "write_file", "memory_commit_archival"]
        used_domain_tool = any(f"Tool {t}" in transcript for t in domain_tools)
        if used_domain_tool:
            outcome_score += 0.25
            structural_notes.append("Domain-relevant tool(s) used")

        # +0.25: final tool result indicates success (last tool line has status ok)
        final_success = '"status": "ok"' in last_tool_line or "status: ok" in last_tool_line.lower()
        if final_success:
            outcome_score += 0.25
            structural_notes.append("Final tool call succeeded")

        outcome_score = round(min(outcome_score, 1.0), 3)

        # ── Layer 3: Quality score — LLM grades against active milestone rubric ──
        if not self.llm:
            return {
                "outcome_score": outcome_score,
                "quality_score": outcome_score,
                "quality_reason": f"No LLM grader. Structural checks: {'; '.join(structural_notes)}",
                "outcome_details": files_str
            }

        md = self._get_milestone_data(category_id)
        rubric  = md["rubric"]
        anchors = md["anchors"]
        rubric_text = "\n".join(f"Level {k[-1]}: {v}" for k, v in rubric.items() if v)
        anchor_text = "\n".join(f"- {a}" for a in anchors)

        # Use the tail of the transcript so file-creation evidence isn't cut off
        transcript_window = transcript[-10000:] if len(transcript) > 10000 else transcript

        prompt = (
            f"You are grading an AI agent's performance on the '{category_id}' capability.\n\n"
            f"## Rubric\n{rubric_text}\n\n"
            f"## Success Anchors\n{anchor_text}\n\n"
            f"## Agent Transcript\n{transcript_window}\n\n"
            f"## Workspace Evidence\n{files_str}\n\n"
            f"Assign a rubric level (1, 2, 3, or 4) based strictly on the rubric above. "
            f"Be critical — only award level 4 for genuinely systematic, complete performance.\n\n"
            f'Output ONLY this JSON: {{"level": <1-4>, "quality_reason": "...", "outcome_details": "..."}}'
        )
        try:
            res = self.llm.complete([{"role": "user", "content": prompt}])
            text = "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text")
            grading = None
            start = text.find("{")
            if start != -1:
                for end in range(len(text), start, -1):
                    try:
                        grading = json.loads(text[start:end])
                        break
                    except json.JSONDecodeError:
                        continue
            if grading:
                level = max(1, min(4, int(grading.get("level", 1))))
                quality_score = round(level / 4.0, 3)
                return {
                    "outcome_score": outcome_score,
                    "quality_score": quality_score,
                    "rubric_level": level,
                    "quality_reason": grading.get("quality_reason", "LLM graded"),
                    "outcome_details": grading.get("outcome_details", files_str)
                }
        except Exception as e:
            _log(f"  Grading LLM call failed: {e}", "WARN")

        # Grading failure: outcome score is reliable, quality score is not
        return {
            "outcome_score": outcome_score,
            "quality_score": 0.0,
            "quality_reason": f"LLM grading failed — quality score unreliable. Structural: {'; '.join(structural_notes)}",
            "outcome_details": files_str,
            "grading_reliable": False
        }

    # ─────────────────────────────────────────────────────────
    # Single task run (one task, one agent execution, one grade)
    # ─────────────────────────────────────────────────────────
    def _run_single_task(self, cat_id, workspace_dir, kernel, task_template_injection):
        """Run one task for a category. Returns (score_data, transcript, task)."""
        from agent_loop import AgentLoop

        # 1. Generate task
        task = self._generate_task(cat_id)

        dispatcher = ToolDispatcher(workspace_dir, kernel)

        # 2. Build system prompt — inject task_template as a mandatory behavioral instruction
        sandbox_loop = AgentLoop(kernel, log_callback=lambda m: None)
        base_system = sandbox_loop._execution_prompt() + "\n\n" + sandbox_loop.build_system_prompt()
        if task_template_injection:
            system_prompt = base_system + f"\n\n## MANDATORY BEHAVIOR FOR THIS EVALUATION\n{task_template_injection}"
        else:
            system_prompt = base_system

        # 3. Build tool list — demand skills minus banned ones
        tools = []
        banned_sandbox_skills = {"skill-forge", "eval-bridge"}
        for skill_name, s_info in kernel.manifest.get("skills", {}).items():
            if s_info.get("type") == "demand" and skill_name not in banned_sandbox_skills:
                for func_name in s_info.get("provided_functions", []):
                    if func_name in TOOL_SCHEMAS:
                        tools.append(TOOL_SCHEMAS[func_name])
        tools.extend([
            {"name": "write_file", "description": "Write a file to the workspace", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}},
            {"name": "read_file", "description": "Read a file from the workspace", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}}}
        ])

        messages = [{"role": "user", "content": f"Task: {task}\nSolve this using your tools."}]
        transcript = f"Task: {task}\n\n"

        # 4. Run agent
        if self.actor_llm:
            for iteration in range(self.max_agent_iterations):
                iter_start = time.time()
                try:
                    res = self.actor_llm.complete(messages, tools=tools, system=system_prompt)
                    content = res.get("content", [])
                    messages.append({"role": "assistant", "content": content})

                    has_tool = False
                    tool_results = []
                    for b in content:
                        if b.get("type") == "text":
                            transcript += f"Agent: {b.get('text')}\n"
                        if b.get("type") == "tool_use":
                            has_tool = True
                            result = dispatcher.dispatch(b["name"], b["input"])
                            r_str = json.dumps(result)
                            transcript += f"Tool {b['name']}: {r_str}\n"
                            tool_results.append({"type": "tool_result", "tool_use_id": b["id"], "content": r_str})

                    iter_time = time.time() - iter_start
                    tool_names = [b["name"] for b in content if b.get("type") == "tool_use"]
                    _log(f"    [{cat_id}] iter {iteration+1}: tools=[{', '.join(tool_names)}] ({iter_time:.1f}s)", "INFO")

                    if not has_tool:
                        break
                    messages.append({"role": "user", "content": tool_results})
                except Exception as loop_e:
                    transcript += f"Error: {loop_e}\n"
                    _log(f"    [{cat_id}] Agent loop error: {loop_e}", "ERR")
                    break

        # 5. Grade
        score_data = self._grade_sandbox(transcript, cat_id, workspace_dir)
        return score_data, transcript, task

    # ─────────────────────────────────────────────────────────
    # Multi-task category evaluation — runs N tasks, averages scores
    # ─────────────────────────────────────────────────────────
    def _eval_single_category(self, cat_id, sandbox_dir, eval_id):
        """Evaluate a single category over N tasks. Each category gets its own BorosKernel
        instance so concurrent evaluations cannot share or corrupt kernel state."""
        cat_start = time.time()
        num_tasks = self.config.get("eval_tasks_per_category", 3)

        md = self._get_milestone_data(cat_id)
        task_template = md["task_template"]
        milestone_level = md["milestone_level"]
        milestone_name  = md["milestone_name"]
        _log(f"  [{cat_id}] Milestone {milestone_level}: {milestone_name} (difficulty={md['difficulty']})", "INFO")

        # Fresh isolated kernel per category — prevents state leakage under concurrency
        _log(f"  [{cat_id}] Loading isolated BorosKernel...", "INFO")
        kernel = BorosKernel()
        for skill_name in kernel.manifest.get("skills", {}):
            kernel.reload_skill(skill_name)
        _log(f"  [{cat_id}] Kernel ready", "OK")

        _log(f"  [{cat_id}] Running {num_tasks} task(s)...", "INFO")

        outcome_scores = []
        quality_scores = []
        combined_transcript = ""
        first_task = None
        last_score_data = {}

        for i in range(num_tasks):
            workspace_dir = os.path.join(sandbox_dir, cat_id, f"task_{i+1}", "workspace")
            os.makedirs(workspace_dir, exist_ok=True)

            _log(f"  [{cat_id}] Task {i+1}/{num_tasks}...", "INFO")
            try:
                score_data, transcript, task = self._run_single_task(
                    cat_id, workspace_dir, kernel, task_template
                )
                outcome_scores.append(score_data["outcome_score"])
                quality_scores.append(score_data["quality_score"])
                combined_transcript += f"\n--- Task {i+1} ---\n{transcript}"
                last_score_data = score_data
                if first_task is None:
                    first_task = task
                blended = round(score_data["outcome_score"] * 0.5 + score_data["quality_score"] * 0.5, 3)
                _log(f"  [{cat_id}] Task {i+1}: outcome={score_data['outcome_score']:.2f} "
                     f"quality={score_data['quality_score']:.2f} blended={blended:.2f}", "OK")
            except Exception as e:
                _log(f"  [{cat_id}] Task {i+1} failed: {e}", "ERR")
                outcome_scores.append(0.0)
                quality_scores.append(0.0)
                combined_transcript += f"\n--- Task {i+1} FAILED: {e} ---\n"

        # Average across all task runs
        avg_outcome = round(sum(outcome_scores) / len(outcome_scores), 3) if outcome_scores else 0.0
        avg_quality = round(sum(quality_scores) / len(quality_scores), 3) if quality_scores else 0.0
        avg_blended = round(avg_outcome * 0.5 + avg_quality * 0.5, 3)

        averaged_score_data = {
            "outcome_score": avg_outcome,
            "quality_score": avg_quality,
            "quality_reason": last_score_data.get("quality_reason", ""),
            "outcome_details": f"Averaged over {num_tasks} task runs. Individual outcomes: {outcome_scores}",
            "task_count": num_tasks,
            "individual_outcome_scores": outcome_scores,
            "individual_quality_scores": quality_scores
        }

        total_time = time.time() - cat_start
        _log(f"  [{cat_id}] FINAL avg outcome={avg_outcome:.2f} quality={avg_quality:.2f} "
             f"blended={avg_blended:.2f} ({num_tasks} tasks, {total_time:.1f}s total)", "OK")

        return cat_id, averaged_score_data, combined_transcript, first_task

    # ─────────────────────────────────────────────────────────
    # Full request processing
    # ─────────────────────────────────────────────────────────
    def _reload_world_model(self):
        """Re-read world_model.json from disk to pick up live changes."""
        try:
            with open(self.world_model_path) as f:
                self.world_model = json.load(f)
        except Exception as e:
            _log(f"Failed to reload world_model.json: {e}", "WARN")

    def _process_request(self, req_path):
        try:
            # Hot-reload world model on every request so new categories are picked up
            self._reload_world_model()

            with open(req_path, "r") as f:
                req = json.load(f)

            eval_id = f"eval-{uuid.uuid4().hex[:8]}"
            cycle = req.get('cycle', 0)
            categories = req.get("categories") or list(self.world_model["categories"].keys())

            _log(f"Processing {eval_id} for cycle {cycle} ({len(categories)} categories)", "START")
            _log(f"  Categories: {', '.join(categories)}")
            request_start = time.time()

            # Each category gets its own kernel — see _eval_single_category
            sandbox_dir = os.path.join(self.sandboxes_dir, eval_id)
            scores = {}
            transcripts = {}
            tasks = {}

            # Process categories with concurrency
            if self.max_concurrency > 1 and len(categories) > 1:
                _log(f"  Running {len(categories)} categories with concurrency={self.max_concurrency}", "INFO")
                with ThreadPoolExecutor(max_workers=self.max_concurrency) as executor:
                    futures = {}
                    for cat_id in categories:
                        future = executor.submit(self._eval_single_category, cat_id, sandbox_dir, eval_id)
                        futures[future] = cat_id

                    for future in as_completed(futures, timeout=self.category_timeout * len(categories)):
                        cat_id = futures[future]
                        try:
                            cat_id, score_data, transcript, task = future.result(timeout=self.category_timeout)
                            scores[cat_id] = {
                                "outcome_score": score_data["outcome_score"],
                                "quality_score": score_data["quality_score"],
                                "outcome_weight": 0.5,
                                "quality_weight": 0.5,
                                "quality_reason": score_data.get("quality_reason", ""),
                                "outcome_details": score_data.get("outcome_details", "")
                            }
                            transcripts[cat_id] = transcript
                            tasks[cat_id] = task
                        except FuturesTimeoutError:
                            _log(f"  [{cat_id}] TIMEOUT after {self.category_timeout}s — scoring 0.0", "ERR")
                            scores[cat_id] = {
                                "outcome_score": 0.0, "quality_score": 0.0,
                                "outcome_weight": 0.5, "quality_weight": 0.5,
                                "quality_reason": f"Category evaluation timed out after {self.category_timeout}s",
                                "outcome_details": "Timeout"
                            }
                        except Exception as e:
                            _log(f"  [{cat_id}] ERROR: {e}", "ERR")
                            scores[cat_id] = {
                                "outcome_score": 0.0, "quality_score": 0.0,
                                "outcome_weight": 0.5, "quality_weight": 0.5,
                                "quality_reason": f"Category evaluation failed: {str(e)}",
                                "outcome_details": "Error"
                            }
            else:
                # Sequential processing with per-category timeout
                for cat_id in categories:
                    try:
                        cat_id, score_data, transcript, task = self._eval_single_category(
                            cat_id, sandbox_dir, eval_id
                        )
                        scores[cat_id] = {
                            "outcome_score": score_data["outcome_score"],
                            "quality_score": score_data["quality_score"],
                            "outcome_weight": 0.5,
                            "quality_weight": 0.5,
                            "quality_reason": score_data.get("quality_reason", ""),
                            "outcome_details": score_data.get("outcome_details", "")
                        }
                        transcripts[cat_id] = transcript
                        tasks[cat_id] = task
                    except Exception as e:
                        _log(f"  [{cat_id}] ERROR: {e}", "ERR")
                        traceback.print_exc()
                        scores[cat_id] = {
                            "outcome_score": 0.0, "quality_score": 0.0,
                            "outcome_weight": 0.5, "quality_weight": 0.5,
                            "quality_reason": f"Category evaluation failed: {str(e)}",
                            "outcome_details": "Error"
                        }

            # Cleanup sandbox
            shutil.rmtree(sandbox_dir, ignore_errors=True)

            # Compute composite: blend outcome (deterministic) and quality (LLM) per category
            def _blended(s):
                return s["outcome_score"] * s["outcome_weight"] + s["quality_score"] * s["quality_weight"]

            # FIX-15: Difficulty scaling.
            absolute_scores = {k: round(_blended(v), 3) for k, v in scores.items()}
            
            total_difficulty_weighted = 0.0
            total_weights = 0.0
            for k, v in scores.items():
                difficulty = self._get_milestone_data(k).get("difficulty", 5)
                weight = difficulty / 10.0
                total_difficulty_weighted += absolute_scores[k] * weight
                total_weights += weight
                
            composite_score = round(total_difficulty_weighted / total_weights, 3) if total_weights > 0 else 0.0

            # ─── Write result to shared/results ───
            result = {
                "request_id": req.get("request_id", "unknown"),
                "eval_id": eval_id,
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
                "cycle": cycle,
                "scores": absolute_scores,
                "composite": composite_score,
                "difficulty_level": {k: self._get_milestone_data(k)["difficulty"] for k in categories},
                "scoring_breakdown": scores
            }

            res_path = os.path.join(self.results_dir, f"{eval_id}.json")
            with open(res_path, "w") as f:
                json.dump(result, f, indent=2)

            # ─── Write to generated-tests/ ───
            tests_dir = os.path.join(self.generated_tests_dir, eval_id)
            os.makedirs(tests_dir, exist_ok=True)
            for cat_id, task in tasks.items():
                with open(os.path.join(tests_dir, f"{cat_id}.json"), "w") as f:
                    json.dump({"category": cat_id, "task": task, "eval_id": eval_id, "cycle": cycle}, f, indent=2)

            # ─── Write to logs/ ───
            log_path = os.path.join(self.logs_dir, f"{eval_id}.log")
            with open(log_path, "w") as f:
                f.write(f"Eval: {eval_id} | Cycle: {cycle} | Categories: {len(categories)}\n")
                f.write(f"Composite Score: {composite_score:.3f}\n")
                f.write("=" * 60 + "\n\n")
                for cat_id, transcript in transcripts.items():
                    f.write(f"--- {cat_id} (score: {scores[cat_id]['outcome_score']:.2f}) ---\n")
                    f.write(transcript)
                    f.write("\n\n")

            # ─── Write to scoring/ ───
            scoring_subdir = os.path.join(self.scoring_dir, eval_id)
            os.makedirs(scoring_subdir, exist_ok=True)
            for cat_id, score_data in scores.items():
                with open(os.path.join(scoring_subdir, f"{cat_id}.json"), "w") as f:
                    json.dump(score_data, f, indent=2)

            # Remove processed request
            os.remove(req_path)

            total_time = time.time() - request_start
            _log(f"Finished {eval_id}: composite={composite_score:.2f} ({len(categories)} cats in {total_time:.1f}s)", "END")
            _log(f"  Scores: {', '.join(f'{k}={v:.2f}' for k, v in result['scores'].items())}")

        except Exception as e:
            _log(f"Error processing request: {e}", "ERR")
            traceback.print_exc()
            if os.path.exists(req_path):
                os.remove(req_path)

if __name__ == "__main__":
    generator = EvalGenerator()
    generator.run()
