"""
Centralized tool schema definitions for all Boros skills.
Each schema follows the Anthropic tool format (name, description, input_schema).
Adapters convert to their native format as needed.
"""

def _s(name, desc, props=None, required=None):
    """Shorthand schema builder."""
    schema = {"name": name, "description": desc, "input_schema": {"type": "object", "properties": props or {}, "required": required or []}}
    return schema

TOOL_SCHEMAS = {
    # ── Loop Orchestrator ──
    "loop_start": _s("loop_start", "Start a new evolution cycle. Initializes state to REFLECT stage and loads context."),
    "loop_advance_stage": _s("loop_advance_stage", "Advance to the next stage: REFLECT → EVOLVE → EVAL → END.", {"current_stage": {"type": "string", "enum": ["REFLECT", "EVOLVE", "EVAL"]}}),
    "loop_end_cycle": _s("loop_end_cycle", "End the current evolution cycle. Increments cycle counter, cleans session."),
    "loop_get_state": _s("loop_get_state", "Get the current loop state (cycle number, stage, mode)."),

    # ── Mode Controller ──
    "mode_get": _s("mode_get", "Get the current operating mode (evolution, supervised, maintenance)."),
    "mode_set": _s("mode_set", "Set the operating mode.", {"mode": {"type": "string", "enum": ["evolution", "supervised", "maintenance"]}}, ["mode"]),


    # ── Memory ──
    "memory_page_in": _s("memory_page_in", "Load data from long-term memory into session context. For evolution_records, use skill= to filter by target skill and outcome= to filter by result (improved/regressed/neutral/baseline). For experiences, use tags= to filter by tag list.", {"source": {"type": "string", "enum": ["scores", "experiences", "evolution_records", "sessions", "session_buffer"]}, "limit": {"type": "integer", "default": 10}, "skill": {"type": "string", "description": "Filter evolution_records by target_skill (partial match)"}, "outcome": {"type": "string", "enum": ["improved", "regressed", "neutral", "baseline"], "description": "Filter evolution_records by actual_outcome"}, "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter experiences by tags (any match)"}}, ["source"]),
    "memory_page_out": _s("memory_page_out", "Write key-value data to the current session buffer.", {"key": {"type": "string"}, "value": {"type": "string"}}, ["key", "value"]),
    "memory_search_sql": _s("memory_search_sql", "Search memory files using a keyword query. Returns matching entries.", {"query": {"type": "string"}}, ["query"]),
    "memory_commit_archival": _s("memory_commit_archival", "Commit an entry to long-term archival memory (experiences).", {"entry_type": {"type": "string", "enum": ["lesson", "observation", "fact"]}, "content": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}}, ["entry_type", "content"]),
    "memory_kg_write": _s("memory_kg_write", "Record a temporal fact about a skill or category in the knowledge graph. Use after evolutions, score changes, and milestone advances. Common predicates: has_score, was_modified, achieved_milestone, caused_delta_in, target_of.", {"subject": {"type": "string", "description": "Skill name or category"}, "predicate": {"type": "string", "description": "Relationship type, e.g. has_score, was_modified, achieved_milestone"}, "object": {"type": "string", "description": "Value or related entity"}, "cycle": {"type": "integer"}, "valid_from": {"type": "string", "description": "ISO timestamp, defaults to now"}, "metadata": {"type": "object"}}, ["subject", "predicate", "object"]),
    "memory_kg_query": _s("memory_kg_query", "Query current or historical facts about a skill or category from the knowledge graph. Returns what is currently true by default. Use include_history=true for full timeline, as_of=<timestamp> for point-in-time queries.", {"subject": {"type": "string"}, "predicate": {"type": "string", "description": "Optional filter by predicate type"}, "as_of": {"type": "string", "description": "ISO timestamp for point-in-time query"}, "include_history": {"type": "boolean", "description": "Include invalidated/past facts"}}, ["subject"]),

    # ── Skill Router ──
    "router_get_tools": _s("router_get_tools", "Get the list of all available tool names and their descriptions."),
    "router_get_budget": _s("router_get_budget", "Get remaining token and tool-call budget for this cycle."),
    "router_manifest": _s("router_manifest", "Get the full skill manifest with dependencies and boot order."),

    # ── Context Orchestration ──
    "context_load": _s("context_load", "Load fresh context at cycle start: identity, scores, hypothesis, recent experiences."),
    "context_get_manifest": _s("context_get_manifest", "Get the context manifest listing what was loaded into the current session."),

    # ── Reflection ──
    "reflection_analyze_trace": _s("reflection_analyze_trace", "Analyze the score history to identify trends, weaknesses, and improvement opportunities.", {"last_n_cycles": {"type": "integer", "default": 5}}),
    "reflection_write_hypothesis": _s("reflection_write_hypothesis", "Write an improvement hypothesis for this cycle.", {"rationale": {"type": "string", "description": "Why this improvement is needed"}, "target_skill": {"type": "string", "description": "Which skill to improve"}, "expected_improvement": {"type": "string", "description": "What metric should improve"}}, ["rationale"]),
    "reflection_read_hypothesis": _s("reflection_read_hypothesis", "Read the current cycle's hypothesis."),

    # ── Meta-Evolution ──
    "evolve_orient": _s("evolve_orient", "Survey scores and identify the weakest skill categories. Returns orientation data for targeting."),
    "evolve_set_target": _s("evolve_set_target", "Set the evolution target for this cycle.", {"target": {"type": "string", "description": "Skill name or file path"}, "category": {"type": "string"}, "approach": {"type": "string"}}, ["target", "approach"]),
    "evolve_propose": _s("evolve_propose", "Create a formal evolution proposal with snapshot.", {"target": {"type": "string", "description": "Skill name or file path modified"}, "snapshot_id": {"type": "string"}, "description": {"type": "string", "description": "What the proposed change does"}, "target_file": {"type": "string", "description": "File path being modified"}, "diff_summary": {"type": "string", "description": "Summary of the code changes"}}, ["target", "snapshot_id", "description", "target_file"]),
    "evolve_apply": _s("evolve_apply", "Commit an approved proposal to the evolution records.", {"proposal_id": {"type": "string"}}, ["proposal_id"]),
    "evolve_rollback": _s("evolve_rollback", "Rollback to a previous snapshot.", {"snapshot_id": {"type": "string"}}, ["snapshot_id"]),
    "evolve_create_skill": _s("evolve_create_skill", "Create a brand new skill with directory structure, manifest entry, and inject its tool schemas.", {"skill_name": {"type": "string"}, "description": {"type": "string"}, "functions": {"type": "array", "items": {"type": "string"}}, "schemas_json": {"type": "string", "description": "JSON string of array of standard tool schema dicts for the new functions. Example: '[{\"name\":\"func\",\"description\":\"...\",\"input_schema\":{...}}]'"}}, ["skill_name", "description", "functions", "schemas_json"]),
    "evolve_modify_loop": _s("evolve_modify_loop", "Propose a modification to the evolution loop stages or parameters.", {"modification": {"type": "string"}, "rationale": {"type": "string"}}, ["modification", "rationale"]),
    "evolve_history": _s("evolve_history", "Read the evolution history (past proposals, verdicts, diffs).", {"limit": {"type": "integer", "default": 10}}),
    "evolve_query_ledger": _s("evolve_query_ledger", "Query the evolution ledger — your institutional memory of every code change and its outcome. Use mode='regressions' to see what failed, mode='skill_stats' with target_skill to see per-skill success rates, mode='file_history' with target_file to see every change to a specific file, mode='improvements' for what worked, mode='recent' for latest entries.", {"mode": {"type": "string", "enum": ["recent", "regressions", "improvements", "skill_stats", "file_history"], "default": "recent"}, "target_file": {"type": "string", "description": "File path for file_history mode"}, "target_skill": {"type": "string", "description": "Skill name for skill_stats mode"}, "limit": {"type": "integer", "default": 20}}),

    # ── Meta-Evaluation ──
    "review_proposal": _s("review_proposal", "Submit a proposal to the independent Meta-Evaluation Review Board (secondary LLM). Returns verdict: apply/reject/modify.", {"proposal_id": {"type": "string"}, "diff": {"type": "string", "description": "The exact block of code that was modified. IMPORTANT: Do NOT put an english explanation here. You MUST output actual python code snippet or unix diff."}, "description": {"type": "string"}, "target_file": {"type": "string"}}, ["proposal_id", "diff", "description"]),
    "review_modify": _s("review_modify", "Request modifications to a proposal based on review feedback.", {"proposal_id": {"type": "string"}, "modifications": {"type": "string"}}, ["proposal_id", "modifications"]),
    "review_criteria_update": _s("review_criteria_update", "Update the review criteria used by the Meta-Evaluation board.", {"criteria": {"type": "object"}}, ["criteria"]),
    "review_history": _s("review_history", "Read past review decisions.", {"limit": {"type": "integer", "default": 10}}),

    # ── Skill Forge ──
    "forge_snapshot": _s("forge_snapshot", "Create a restorable snapshot of a target's current state before modification. Target can be skill name or file path.", {"target": {"type": "string"}}, ["target"]),
    "forge_validate": _s("forge_validate", "Validate a python file or skill's Python files for syntax errors.", {"target": {"type": "string"}}, ["target"]),
    "forge_test_suite": _s("forge_test_suite", "Run the test suite for a target. Returns pass/fail and output.", {"target": {"type": "string"}}, ["target"]),
    "forge_apply_diff": _s("forge_apply_diff", "Apply a diff to a skill's function file.", {"target_file": {"type": "string"}, "replacement_chunks": {"type": "array", "items": {"type": "object", "properties": {"target_content": {"type": "string"}, "replacement_content": {"type": "string"}}}}}, ["target_file", "replacement_chunks"]),
    "forge_rollback": _s("forge_rollback", "Rollback a target to a previous snapshot.", {"target": {"type": "string"}, "snapshot_id": {"type": "string"}}, ["target", "snapshot_id"]),
    "forge_invoke": _s("forge_invoke", "Invoke a specific function from a skill for testing.", {"function_name": {"type": "string"}, "params": {"type": "object"}}, ["function_name"]),
    "forge_create_skill": _s("forge_create_skill", "Scaffold a new skill directory with standard structure.", {"skill_name": {"type": "string"}, "description": {"type": "string"}, "functions": {"type": "array", "items": {"type": "string"}}}, ["skill_name", "description", "functions"]),
    "forge_read_skill_md": _s("forge_read_skill_md", "Read the SKILL.md for a skill. Returns full content and parsed sections. Use before editing.", {"skill_name": {"type": "string"}}, ["skill_name"]),
    "forge_edit_skill_md": _s("forge_edit_skill_md", "Edit a specific section of a SKILL.md file. This is Escalation Ladder Step 1 — always try semantic changes before code changes.", {"skill_name": {"type": "string"}, "section_name": {"type": "string", "description": "The ## section header to replace (e.g. 'Role', 'Rules', 'Pipeline')"}, "new_content": {"type": "string", "description": "The new content for this section"}}, ["skill_name", "section_name", "new_content"]),

    # ── Reasoning ──
    "reason_decompose": _s("reason_decompose", "Decompose a complex problem into sub-problems. Returns structured breakdown.", {"problem": {"type": "string"}}, ["problem"]),
    "reason_evaluate_options": _s("reason_evaluate_options", "Evaluate multiple options against criteria. Returns ranked assessment.", {"options": {"type": "array", "items": {"type": "string"}}, "criteria": {"type": "string"}}, ["options", "criteria"]),
    "reason_check_logic": _s("reason_check_logic", "Check an argument for logical consistency. Returns assessment.", {"argument": {"type": "string"}}, ["argument"]),
    "reason_generate_plan": _s("reason_generate_plan", "Generate a structured step-by-step execution plan for a complex problem.", {"problem": {"type": "string"}}, ["problem"]),

    # ── Tool Use ──
    "tool_terminal": _s("tool_terminal", "Execute a shell command. Returns stdout, stderr, returncode. Use background=true for long-running processes.", {"command": {"type": "string"}, "background": {"type": "boolean", "default": False}}, ["command"]),
    "tool_terminal_input": _s("tool_terminal_input", "Send stdin input to a background job.", {"job_id": {"type": "string"}, "text": {"type": "string"}}, ["job_id", "text"]),
    "tool_terminal_kill": _s("tool_terminal_kill", "Terminate a background job.", {"job_id": {"type": "string"}}, ["job_id"]),
    "tool_file_edit_diff": _s("tool_file_edit_diff", "Apply surgical find-and-replace patches to a file. Each chunk replaces the first occurrence of target_content with replacement_content.", {"target_file": {"type": "string"}, "replacement_chunks": {"type": "array", "items": {"type": "object", "properties": {"target_content": {"type": "string"}, "replacement_content": {"type": "string"}}, "required": ["target_content", "replacement_content"]}}}, ["target_file", "replacement_chunks"]),
    "tool_file_write": _s("tool_file_write", "Write content to a file, creating it if it doesn't exist. Use this to create new Python skill functions from scratch. Python files are syntax-checked before confirming.", {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),

    # ── Web Research ──
    "research_browse": _s("research_browse", "Fetch and read content from a URL.", {"url": {"type": "string"}}, ["url"]),
    "research_search_engine": _s("research_search_engine", "Search the web for information.", {"query": {"type": "string"}}, ["query"]),
    "research_archive_source": _s("research_archive_source", "Archive a web source to local memory for future reference.", {"url": {"type": "string"}, "tag": {"type": "string"}}, ["url"]),

    # ── Eval Bridge ──
    "eval_request": _s("eval_request", "Submit an evaluation request to the Eval Generator sandbox. Returns request_id.", {"cycle": {"type": "integer"}, "categories": {"type": "array", "items": {"type": "string"}}}, ["cycle"]),
    "eval_read_scores": _s("eval_read_scores", "Read the latest evaluation scores. Checks eval-generator results directory.", {"eval_id": {"type": "string", "description": "Optional specific eval ID to read"}}),
    "eval_backfill": _s("eval_backfill", "Backfill missing scores for a given cycle.", {"cycle": {"type": "integer"}}, ["cycle"]),
    "eval_check_regression": _s("eval_check_regression", "Compare current scores against high-water marks. Auto-rollbacks on regression.", {"current_scores": {"type": "object"}}, ["current_scores"]),
    "eval_update_high_water": _s("eval_update_high_water", "Update high-water marks if current scores exceed them.", {"scores": {"type": "object"}}, ["scores"]),
    "eval_check_milestone": _s("eval_check_milestone", "Check if any category has cleared its current milestone and advance world_model.json if so. Call after each eval."),

    # ── Eval Utility ──
    "generate_evaluation_artifact": _s("generate_evaluation_artifact", "Generate a JSON artifact file for evaluation in the eval-generator shared artifacts directory.", {"artifact_name": {"type": "string", "description": "Name for the artifact file"}, "content": {"type": "object", "description": "JSON content to write to the artifact"}}, ["artifact_name", "content"]),

    # ── Civilization ──
    "civ_get_identity": _s("civ_get_identity", "Read this instance's identity (instance_id, parents, generation, birth_type, world_model_hash)."),
    "civ_record_gene": _s("civ_record_gene", "Record a successful mutation as a gene in the genome. Called automatically by loop_end_cycle on improvement.", {"cycle": {"type": "integer"}, "target_skill": {"type": "string"}, "target_file": {"type": "string"}, "approach": {"type": "string"}, "diff": {"type": "string"}, "score_delta": {"type": "number"}, "score_before": {"type": "object"}, "score_after": {"type": "object"}, "proposal_id": {"type": "string"}, "review_verdict": {"type": "string"}}, ["cycle"]),
    "civ_read_genome": _s("civ_read_genome", "Read the genome — all genes this instance has accumulated. Supports filtering by origin and category.", {"filter_origin": {"type": "string", "enum": ["evolved", "inherited", "bred"]}, "filter_category": {"type": "string"}, "limit": {"type": "integer"}}),
    "civ_fork_child": _s("civ_fork_child", "Handle identity + genome + lineage for a fork operation. Generates child ID and prepares identity seed."),
    "civ_heartbeat": _s("civ_heartbeat", "Write a heartbeat broadcast with current instance state (identity, scores, genes, children).", {"cycle": {"type": "integer"}, "scores": {"type": "object"}, "last_outcome": {"type": "string"}, "last_delta": {"type": "number"}, "last_category": {"type": "string"}}, ["cycle"]),
    "civ_lineage_read": _s("civ_lineage_read", "Read this instance's lineage record — identity, events, gene count, scores."),
    "civ_lineage_diff": _s("civ_lineage_diff", "Compare this instance with another Boros instance. Returns shared genes, score comparison, world model divergence.", {"other_path": {"type": "string", "description": "Path to the other Boros instance root"}}, ["other_path"]),
}
