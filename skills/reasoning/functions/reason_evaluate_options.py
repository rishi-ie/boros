
import re

def reason_evaluate_options(options: list[str], criteria: str) -> dict:
    # This is a simplified example. A full implementation would likely involve
    # more sophisticated NLP for criteria parsing and a more robust scoring model.

    ranked_options = []
    
    # 1. Basic Criteria Parsing: Identify keywords and potential constraints
    # This is a simplified approach, a more advanced version would use NLU.
    criteria_keywords = [word.lower() for word in re.findall(r'\b\w+\b', criteria) if len(word) > 2]
    
    # Simple scoring based on keyword matching
    for i, option in enumerate(options):
        score = 0
        rationale = []
        lower_option = option.lower()

        # Check for positive matches
        for keyword in criteria_keywords:
            if keyword in lower_option:
                score += 1
                rationale.append(f"Matches '{keyword}'")

        # Basic trade-off (example: 'cost' vs 'quality') - highly simplified
        if "cost" in criteria.lower() and "low cost" in lower_option:
            score += 2 # Higher score for explicit low cost
            rationale.append("Prioritizes low cost as per criteria")
        elif "quality" in criteria.lower() and "high quality" in lower_option:
            score += 2 # Higher score for explicit high quality
            rationale.append("Prioritizes high quality as per criteria")

        # Implicit constraint detection (example: "safe" or "secure")
        if "safe" in criteria.lower() or "secure" in criteria.lower():
            if "risk" not in lower_option and "vulnerable" not in lower_option:
                score += 1
                rationale.append("No explicit safety/security risks mentioned, aligning with implicit constraints")
            else:
                score -= 1 # Penalize if risks are mentioned
                rationale.append("Potential safety/security concerns identified")

        ranked_options.append({
            "option": option,
            "score": score,
            "rationale": ". ".join(rationale) if rationale else "No specific criteria matches found."
        })
    
    # Sort options by score in descending order
    ranked_options.sort(key=lambda x: x["score"], reverse=True)

    # Generate an artifact for evaluation purposes
    if kernel:
        kernel.invoke("eval_util", "generate_evaluation_artifact", {"content": {"options": ranked_options, "criteria": criteria}, "artifact_name": "evaluated_options"})

    return {"status": "ok", "ranked_options": ranked_options, "note": "Options evaluated with a basic scoring model for generative depth."}
