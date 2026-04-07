
def reason_check_logic(params: dict, kernel=None) -> dict:
    """Check an argument for logical consistency using LLM analysis."""
    argument = params.get("argument", "")
    if not argument:
        return {"status": "error", "message": "argument required"}

    if kernel and hasattr(kernel, "evolution_llm"):
        prompt = (
            f"You are a logic verification assistant. Analyze the following argument for logical consistency.\n\n"
            f"Argument: {argument}\n\n"
            f"Check for:\n"
            f"1. Internal contradictions\n"
            f"2. Unsupported assumptions\n"
            f"3. Invalid reasoning steps (non-sequiturs, circular reasoning)\n"
            f"4. Whether the conclusion follows from the premises\n\n"
            f"Respond ONLY as a valid JSON object:\n"
            f'{{"valid": true/false, "issues": ["issue1", "issue2"], "verdict": "brief summary"}}'
        )
        try:
            res = kernel.evolution_llm.complete(
                [{"role": "user", "content": prompt}],
                system="You are a logic checker. Output only the JSON object."
            )
            text = "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text")
            import re, json
            start = text.find("{")
            if start != -1:
                for end in range(len(text), start, -1):
                    try:
                        result = json.loads(text[start:end])
                        return {"status": "ok", "argument": argument, **result}
                    except json.JSONDecodeError:
                        continue
            return {"status": "ok", "argument": argument, "valid": None,
                    "issues": [], "verdict": text.strip()[:500]}
        except Exception as e:
            return {"status": "error", "message": f"Logic check failed: {e}"}

    # Fallback: basic heuristic checks
    issues = []
    lower = argument.lower()
    if " because " in lower and lower.index(" because ") > lower.rindex(" because "):
        issues.append("Possible circular reasoning detected.")
    if "always" in lower or "never" in lower:
        issues.append("Absolute claim detected — verify universality.")
    return {
        "status": "ok",
        "argument": argument,
        "valid": len(issues) == 0,
        "issues": issues,
        "verdict": "Heuristic check only — LLM unavailable.",
        "method": "heuristic"
    }
