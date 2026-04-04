
import os, json, glob
def reflection_analyze_trace(params: dict, kernel=None) -> dict:
    """Analyze score history to identify trends, weaknesses, and opportunities."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    last_n = params.get("last_n_cycles", 5)

    # Read score history
    score_file = os.path.join(boros_dir, "memory", "score_history.jsonl")
    entries = []
    if os.path.exists(score_file):
        with open(score_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    recent = entries[-last_n:] if entries else []

    # Read eval results directory
    results_dir = os.path.join(boros_dir, "eval-generator", "shared", "results")
    eval_results = []
    if os.path.isdir(results_dir):
        for rf in sorted(glob.glob(os.path.join(results_dir, "*.json")))[-last_n:]:
            try:
                with open(rf) as f:
                    eval_results.append(json.load(f))
            except Exception:
                pass

    # Aggregate scores by category
    category_scores = {}
    for entry in recent + eval_results:
        scores = entry.get("scores", entry)
        if isinstance(scores, dict):
            for cat, score in scores.items():
                if isinstance(score, (int, float)):
                    if cat not in category_scores:
                        category_scores[cat] = []
                    category_scores[cat].append(score)

    # Read actual active categories from world_model.json
    wm_path = os.path.join(boros_dir, "world_model.json")
    active_categories = {}
    if os.path.exists(wm_path):
        try:
            with open(wm_path) as f:
                wm = json.load(f)
                active_categories = wm.get("categories", {})
        except Exception:
            pass

    # Calculate averages and trends only for active categories
    analysis = {}
    weakest_category = None
    lowest_avg = 1.0
    
    # Initialize all active categories with 0.0 if they have no scores
    for cat in active_categories:
        if cat not in category_scores:
            category_scores[cat] = []

    for cat, scores in category_scores.items():
        if cat not in active_categories:
            continue # Ignore categories from old score history that are now deleted

        avg = sum(scores) / len(scores) if scores else 0.0
        trend = "stable"
        if len(scores) >= 2:
            if scores[-1] > scores[0]:
                trend = "improving"
            elif scores[-1] < scores[0]:
                trend = "declining"
        analysis[cat] = {"average": round(avg, 3), "trend": trend, "samples": len(scores), "latest": scores[-1] if scores else 0}
        
        # We want to strictly find the weakest category
        if avg <= lowest_avg:
            lowest_avg = avg
            weakest_category = cat

    # Extract detailed feedback for the weakest category from recent eval results
    feedback = {"quality_reason": "Not provided", "outcome_details": "No specific failures logged"}
    if weakest_category and eval_results:
        latest = eval_results[-1]
        breakdown = latest.get("scoring_breakdown", {}).get(weakest_category, {})
        feedback["quality_reason"] = breakdown.get("quality_reason", feedback["quality_reason"])
        feedback["outcome_details"] = breakdown.get("outcome_details", feedback["outcome_details"])

    return {
        "status": "ok",
        "total_entries": len(entries),
        "analyzed": len(recent),
        "category_analysis": analysis,
        "weakest_category": weakest_category,
        "weakest_score": round(lowest_avg, 3),
        "recommendation": _generate_detailed_recommendation(weakest_category, lowest_avg, feedback) if weakest_category else "No score data available. Run evaluations first."
    }

def _generate_detailed_recommendation(category, score, feedback):
    reason = feedback.get("quality_reason", "No specific reason given")
    outcome = feedback.get("outcome_details", "No detailed outcomes logged")
    
    recommendation = (
        f"To improve '{category}' (avg: {score:.3f}), you must address actual evaluation failures.\n"
        f"Eval Sandbox Feedback: {reason}\n"
        f"Outcome Details: {outcome}\n\n"
    )

    if category == "memory_continuity":
        if "fatal tool errors" in reason.lower() or "failed tool call" in outcome.lower() or "tool error" in outcome.lower() or "transcript ends before task iterations" in reason.lower():
            recommendation += (
                "**Actionable Memory & Continuity Insights (Tool Errors Detected):**\n"
                "- **Environment Initialization:** Ensure the necessary files and directories are created and correctly populated *before* attempting core task logic. Verify paths, permissions, and file content immediately after creation using `tool_terminal` (`type` or `dir`).\n"
                "- **Tool Call Sequencing:** Explicitly plan the order of tool calls. If a task requires writing a file and then executing a script that reads that file, ensure the write operation completes successfully before the execute operation begins. Look for missing intermediate verification steps.\n"
                "- **Pre-computation/Pre-analysis:** Before beginning an iterative task, perform an initial `tool_terminal` `dir` listing of the eval sandbox to understand the initial state and potential pitfalls. Use `tool_terminal` `type` to inspect any provided files. This helps prevent blind execution.\n"
                "- **Failure Recovery Plan:** If an initial tool call fails, log the error to episodic memory (`memory_commit_archival`) and try a different approach or re-verify the environment. Do not proceed with subsequent steps if foundational tools have failed.\n"
                "- **Verify Execution Context:** Ensure the executed script or command has the correct working directory and necessary arguments. Check if a script needs to be made executable or if specific interpreters are required.\n"
                "- **Iterative Trace Analysis:** For multi-iteration tasks, specifically review the trace for the *first* iteration's success. Failures there often propagate. Look for evidence of file creation, modification, and successful execution of the *initial* steps within the evaluation environment.\n"
            )
        else:
            recommendation += (
                "**Memory & Continuity Insights:**\n"
                "- **Structured Recall:** Ensure that relevant past experiences and rules are actively retrieved and applied to current decision-making. Is `memory_page_in` being called with appropriate `source` and `limit` to get necessary context?\n"
                "- **Abstraction Refinement:** If general rules are being abstracted, are they accurate and robust enough to handle variations and edge cases? Consider how new information refines existing abstractions.\n"
                "- **Adaptive Planning:** Does the agent's action plan dynamically adapt based on the outcomes of previous actions? Look for explicit logic that modifies the plan based on success or failure.\n"
                "- **Avoiding Regression:** Implement checks to ensure that new actions do not inadvertently reintroduce previously solved failure modes. Leverage historical `evolution_records` and `experiences` for this.\n"
                "- **Contextual Awareness:** Verify that the system is leveraging its current session context effectively, not just raw memory entries. Is `context_load` being used at the start of cycles to get relevant information?\n"
            )
    elif category == "reasoning_architecture":
        recommendation += (
            f"**Actionable Architectural Insights:**\n"
            f"- Consider reviewing the current flow of information between skills. Are there bottlenecks or inefficient data transfers?\n"
            f"- Evaluate the modularity and separation of concerns within the code. Can any components be more independent?\n"
            f"- Look for opportunities to introduce caching or optimize frequently accessed data structures.\n"
            f"- Ensure that error handling and recovery mechanisms are robust and well-defined.\n"
            f"- If outcome details were more granular, we could pinpoint exact code sections. Future evaluations should aim to log more specific failure points (e.g., line numbers, specific API calls that failed).\n\n"
        )
    
    recommendation += (
        f"Generate a hypothesis that makes CONCRETE logical and algorithmic improvements. Do NOT just change prompt strings or formatting. Look deeply at the underlying data structures, API interactions, or workflow constraints causing this failure."
    )
    
    return recommendation
