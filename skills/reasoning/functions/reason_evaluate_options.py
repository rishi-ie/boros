
import re

def reason_evaluate_options(params: dict, kernel=None) -> dict:
    """Evaluate multiple options against criteria. Returns ranked assessment."""
    options = params.get("options", [])
    criteria = params.get("criteria", "")

    if not options:
        return {"status": "error", "message": "options list required"}
    if not criteria:
        return {"status": "error", "message": "criteria string required"}

    # Prefer LLM-based evaluation when available
    if kernel and hasattr(kernel, "evolution_llm"):
        prompt = (
            f"You are a structured decision-making assistant. Evaluate each option below against the stated criteria.\n\n"
            f"Criteria: {criteria}\n\n"
            f"Options:\n" + "\n".join(f"{i+1}. {o}" for i, o in enumerate(options)) + "\n\n"
            f"For each option provide a score (0-10) and a concise rationale. "
            f"Respond ONLY as a valid JSON array:\n"
            f'[{{"option": "...", "score": 8, "rationale": "..."}}]'
        )
        try:
            res = kernel.evolution_llm.complete(
                [{"role": "user", "content": prompt}],
                system="You are a structured evaluator. Output only the JSON array."
            )
            text = "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text")
            match = re.search(r'\[.*\]', text, flags=re.DOTALL)
            if match:
                ranked = __import__("json").loads(match.group())
                ranked.sort(key=lambda x: x.get("score", 0), reverse=True)
                return {"status": "ok", "ranked_options": ranked, "method": "llm"}
        except Exception as e:
            print(f"reason_evaluate_options: LLM call failed ({e}), falling back to heuristic.")

    # Heuristic fallback: keyword scoring
    criteria_keywords = [w.lower() for w in re.findall(r'\b\w+\b', criteria) if len(w) > 2]
    ranked = []
    for option in options:
        score = 0
        rationale = []
        lower_opt = option.lower()
        for kw in criteria_keywords:
            if kw in lower_opt:
                score += 1
                rationale.append(f"matches '{kw}'")
        ranked.append({
            "option": option,
            "score": score,
            "rationale": "; ".join(rationale) if rationale else "No keyword matches found."
        })
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return {"status": "ok", "ranked_options": ranked, "method": "heuristic"}
