
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
        "recommendation": _generate_detailed_recommendation(
            weakest_category, lowest_avg, feedback,
            cat_data=active_categories.get(weakest_category)
        ) if weakest_category else "No score data available. Run evaluations first."
    }

def _generate_detailed_recommendation(category, score, feedback, cat_data=None):
    reason = feedback.get("quality_reason", "No specific reason given")
    outcome = feedback.get("outcome_details", "No detailed outcomes logged")

    recommendation = (
        f"To improve '{category}' (avg: {score:.3f}), address the actual evaluation failures below.\n"
        f"Eval Feedback: {reason}\n"
        f"Outcome Details: {outcome}\n\n"
    )

    # Pull insights dynamically from world model category definition
    if cat_data:
        failure_modes = cat_data.get("failure_modes", [])
        anchors = cat_data.get("anchors", [])
        rubric = cat_data.get("rubric", {})
        related_skills = cat_data.get("related_skills", [])

        if failure_modes:
            recommendation += "**Known Failure Modes to Address:**\n"
            for fm in failure_modes:
                recommendation += f"- {fm}\n"
            recommendation += "\n"

        if anchors:
            recommendation += "**Target Anchors (what the eval checks for):**\n"
            for anchor in anchors:
                recommendation += f"- {anchor}\n"
            recommendation += "\n"

        if rubric:
            current_level = "level_1"
            if score >= 0.75:
                current_level = "level_3"
            elif score >= 0.5:
                current_level = "level_2"
            next_level = {"level_1": "level_2", "level_2": "level_3", "level_3": "level_4"}.get(current_level, "level_4")
            current_desc = rubric.get(current_level, "")
            next_desc = rubric.get(next_level, "")
            if current_desc and next_desc:
                recommendation += f"**Current Level ({current_level}):** {current_desc}\n"
                recommendation += f"**Target Next Level ({next_level}):** {next_desc}\n\n"

        if related_skills:
            recommendation += f"**Skills to Target:** {', '.join(related_skills)}\n\n"

    recommendation += (
        "Generate a hypothesis that makes CONCRETE logical and algorithmic improvements. "
        "Do NOT change only prompt strings, comments, or formatting. "
        "Look at the underlying data structures, control flow, and tool interactions causing failures."
    )

    return recommendation
