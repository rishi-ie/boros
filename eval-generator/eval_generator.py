import os, sys, time, json, uuid, datetime, shutil
import random
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError

boros_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from boros.adapters import load_adapter
from boros.kernel import BorosKernel
from boros.tool_schemas import TOOL_SCHEMAS
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
    # Task generation
    # ─────────────────────────────────────────────────────────
    def _generate_task(self, category_id):
        cat = self.world_model["categories"].get(category_id)
        if not cat or not self.llm:
            return "Write a script that prints Hello World to output.txt."

        # Build rich context from world model fields
        anchors = cat.get("anchors", [])
        rubric_l4 = cat.get("rubric", {}).get("level_4", "Excellent performance")
        exec_pattern = cat.get("execution_pattern", {})
        failure_modes = cat.get("failure_modes", [])

        # Pick a random anchor and failure mode to vary tasks
        import random
        anchor = random.choice(anchors) if anchors else "general capability"
        failure = random.choice(failure_modes) if failure_modes else "generic failure"

        prompt = (
            f"Create a concrete, verifiable programming task that tests the '{category_id}' capability.\n\n"
            f"The task must specifically test this anchor criterion: '{anchor}'\n"
            f"The gold standard (Level 4) is: '{rubric_l4}'\n"
            f"Design the task to expose this failure mode: '{failure}'\n\n"
            f"Execution pattern the agent should follow:\n"
            + "\n".join(f"  {k}: {v}" for k, v in exec_pattern.items()) + "\n\n"
            f"The task must be executable in a python sandbox and verifiable by checking file outputs. "
            f"Output just the task prompt, nothing else."
        )
        try:
            res = self.llm.complete([{"role": "user", "content": prompt}], system="You generate targeted evaluation tasks. Output only the task prompt.")
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

        has_error = "Error:" in transcript
        no_files = len(file_list) == 0

        if has_error or no_files:
            reason = "Task execution failed objectively. "
            if has_error:
                reason += "Transcript contains fatal tool errors. "
            if no_files:
                reason += "Agent failed to produce any artifacts. "
            return {"score": 0.0, "quality_reason": reason, "outcome_details": files_str}

        # ── Layer 2: Structural content checks ───────────────────
        structural_score = 0.0
        structural_notes = []

        # Check output files have non-trivial content
        non_empty_files = 0
        for fname in file_list:
            fpath = os.path.join(workspace_dir, fname)
            try:
                size = os.path.getsize(fpath)
                if size > 10:
                    non_empty_files += 1
            except OSError:
                pass
        if non_empty_files > 0:
            structural_score += 0.3
            structural_notes.append(f"{non_empty_files} non-empty output file(s)")

        # Check transcript shows multi-step tool usage (not just one tool call)
        tool_call_count = transcript.count("Tool ")
        if tool_call_count >= 2:
            structural_score += 0.1
            structural_notes.append(f"{tool_call_count} tool calls observed")

        # Check if transcript shows task completion signal
        completion_signals = ["status: ok", "successfully", "complete", "finished", "done"]
        if any(sig in transcript.lower() for sig in completion_signals):
            structural_score += 0.1
            structural_notes.append("Completion signal detected in transcript")

        # ── Layer 3: LLM grades against discrete rubric levels ───
        if not self.llm:
            final_score = min(structural_score + 0.3, 1.0)
            return {
                "score": round(final_score, 3),
                "quality_reason": f"No LLM grader. Structural checks: {'; '.join(structural_notes)}",
                "outcome_details": files_str
            }

        cat = self.world_model["categories"].get(category_id, {})
        rubric = cat.get("rubric", {})
        rubric_text = "\n".join(f"Level {k[-1]}: {v}" for k, v in rubric.items() if v)
        anchors = cat.get("anchors", [])
        anchor_text = "\n".join(f"- {a}" for a in anchors)

        prompt = (
            f"You are grading an AI agent's performance on the '{category_id}' capability.\n\n"
            f"## Rubric\n{rubric_text}\n\n"
            f"## Success Anchors\n{anchor_text}\n\n"
            f"## Agent Transcript\n{transcript[:3000]}\n\n"
            f"## Workspace Evidence\n{files_str}\n\n"
            f"Assign a rubric level (1, 2, 3, or 4) based strictly on the rubric above. "
            f"Be critical — only award level 4 for genuinely systematic, complete performance.\n\n"
            f'Output ONLY this JSON: {{"level": <1-4>, "quality_reason": "...", "outcome_details": "..."}}'
        )
        try:
            res = self.llm.complete([{"role": "user", "content": prompt}])
            text = "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text")
            # Safely extract JSON
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
                # Convert rubric level (1-4) to normalized score (0.25-1.0)
                # Blend with structural checks for robustness
                llm_score = level / 4.0
                final_score = round((llm_score * 0.7) + (structural_score * 0.3), 3)
                return {
                    "score": final_score,
                    "rubric_level": level,
                    "quality_reason": grading.get("quality_reason", "LLM graded"),
                    "outcome_details": grading.get("outcome_details", files_str)
                }
        except Exception as e:
            _log(f"  Grading LLM call failed: {e}", "WARN")

        # Grading failure: use structural score only, flag as unreliable
        final_score = round(min(structural_score, 0.4), 3)
        return {
            "score": final_score,
            "quality_reason": f"LLM grading failed — structural score only. Notes: {'; '.join(structural_notes)}",
            "outcome_details": files_str,
            "grading_reliable": False
        }

    # ─────────────────────────────────────────────────────────
    # Single-category evaluation (runs in thread)
    # ─────────────────────────────────────────────────────────
    def _eval_single_category(self, cat_id, sandbox_dir, kernel, eval_id):
        """Evaluate a single category. Returns (cat_id, score_data, transcript, task)."""
        cat_start = time.time()
        cat_dir = os.path.join(sandbox_dir, cat_id)
        workspace_dir = os.path.join(cat_dir, "workspace")
        os.makedirs(workspace_dir, exist_ok=True)

        # 1. Generate task
        _log(f"  [{cat_id}] Generating task...", "INFO")
        task = self._generate_task(cat_id)
        _log(f"  [{cat_id}] Task generated ({len(task)} chars, {time.time()-cat_start:.1f}s)", "OK")

        dispatcher = ToolDispatcher(workspace_dir, kernel)

        # 2. Run mini agent loop
        from boros.agent_loop import AgentLoop
        sandbox_loop = AgentLoop(kernel, log_callback=lambda m: None)
        system_prompt = sandbox_loop._execution_prompt() + "\n\n" + sandbox_loop.build_system_prompt()
        
        messages = [{"role": "user", "content": f"Task: {task}\nSolve this using your tools."}]

        # Dynamically load all demand tools to ensure the Sandbox can actually test new capabilities.
        # We explicitly ban 'skill-forge' and 'eval-bridge' to prevent the Sandbox from recursively editing the main Boros codebase or starting nested evals.
        tools = []
        banned_sandbox_skills = {"skill-forge", "eval-bridge"}
        for skill_name, s_info in kernel.manifest.get("skills", {}).items():
            if s_info.get("type") == "demand" and skill_name not in banned_sandbox_skills:
                for func_name in s_info.get("provided_functions", []):
                    if func_name in TOOL_SCHEMAS:
                        tools.append(TOOL_SCHEMAS[func_name])

        tools.extend([
            {"name": "write_file", "description": "Write a file", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}},
            {"name": "read_file", "description": "Read a file", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}}}
        ])

        transcript = f"Task: {task}\n\n"

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
                    _log(f"  [{cat_id}] Iteration {iteration+1}/{self.max_agent_iterations}: "
                         f"tools=[{', '.join(tool_names)}] ({iter_time:.1f}s)", "INFO")

                    if not has_tool:
                        _log(f"  [{cat_id}] Agent finished (no more tool calls)", "OK")
                        break
                    messages.append({"role": "user", "content": tool_results})
                except Exception as loop_e:
                    transcript += f"Error: {loop_e}\n"
                    _log(f"  [{cat_id}] Agent loop error: {loop_e}", "ERR")
                    break

        # 3. Grade
        _log(f"  [{cat_id}] Grading...", "INFO")
        grade_start = time.time()
        score_data = self._grade_sandbox(transcript, cat_id, workspace_dir)
        score = score_data["score"]
        grade_time = time.time() - grade_start

        total_time = time.time() - cat_start
        _log(f"  [{cat_id}] Score: {score:.2f} (grade: {grade_time:.1f}s, total: {total_time:.1f}s)", "OK")

        return cat_id, score_data, transcript, task

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

            # Create a SINGLE kernel for all categories
            _log("  Loading BorosKernel...", "INFO")
            kernel = BorosKernel()
            for skill_name in kernel.manifest.get("skills", {}):
                kernel.reload_skill(skill_name)
            _log("  BorosKernel loaded and skills reloaded", "OK")

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
                        future = executor.submit(self._eval_single_category, cat_id, sandbox_dir, kernel, eval_id)
                        futures[future] = cat_id

                    for future in as_completed(futures, timeout=self.category_timeout * len(categories)):
                        cat_id = futures[future]
                        try:
                            cat_id, score_data, transcript, task = future.result(timeout=self.category_timeout)
                            score = score_data["score"]
                            scores[cat_id] = {
                                "outcome_score": score,
                                "quality_score": score,
                                "outcome_weight": 0.5,
                                "quality_weight": 0.5,
                                "quality_reason": score_data["quality_reason"],
                                "outcome_details": score_data["outcome_details"]
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
                            cat_id, sandbox_dir, kernel, eval_id
                        )
                        score = score_data["score"]
                        scores[cat_id] = {
                            "outcome_score": score,
                            "quality_score": score,
                            "outcome_weight": 0.5,
                            "quality_weight": 0.5,
                            "quality_reason": score_data["quality_reason"],
                            "outcome_details": score_data["outcome_details"]
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

            # Compute composite
            total_score = sum(s["outcome_score"] for s in scores.values())
            composite_score = total_score / len(categories) if categories else 0.0

            # ─── Write result to shared/results ───
            result = {
                "request_id": req.get("request_id", "unknown"),
                "eval_id": eval_id,
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
                "cycle": cycle,
                "scores": {k: v["outcome_score"] for k, v in scores.items()},
                "composite": composite_score,
                "difficulty_level": 5,
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
