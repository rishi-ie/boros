
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

    # Fallback: heuristic checks when LLM unavailable
    issues = []
    lower = argument.lower()
    sentences = [s.strip() for s in lower.replace(".", ". ").split(". ") if s.strip()]

    # Circular reasoning: conclusion restates premise (first and last sentence overlap heavily)
    if len(sentences) >= 2:
        first_words = set(sentences[0].split())
        last_words = set(sentences[-1].split())
        stop_words = {"the", "a", "an", "is", "it", "in", "of", "and", "or", "to", "that", "this", "we", "so"}
        overlap = (first_words - stop_words) & (last_words - stop_words)
        if len(overlap) >= 3:
            issues.append(f"Possible circular reasoning: conclusion echoes premise ({', '.join(list(overlap)[:4])}).")

    # Absolute claims without qualification
    absolute_terms = ["always", "never", "everyone", "nobody", "all", "none", "impossible", "guaranteed", "certainly"]
    found_absolutes = [t for t in absolute_terms if t in lower.split()]
    if found_absolutes:
        issues.append(f"Absolute claim(s) detected ({', '.join(found_absolutes)}) — verify universality.")

    # Non-sequitur signal: "therefore" / "thus" used without a premise chain
    conclusion_markers = ["therefore", "thus", "hence", "so", "consequently"]
    has_conclusion_marker = any(m in lower for m in conclusion_markers)
    has_premise_marker = any(m in lower for m in ["because", "since", "given that", "as", "due to"])
    if has_conclusion_marker and not has_premise_marker:
        issues.append("Conclusion asserted without explicit premise (non-sequitur risk).")

    # Contradiction: negation of an earlier claim in the same argument
    positive_claims = [w for w in lower.split() if len(w) > 4 and w.isalpha()]
    negated = [w for w in lower.split() if w.startswith("not") or w.startswith("n't")]
    negated_roots = [w[3:] if w.startswith("not") else w[:-3] for w in negated]
    contradictions = [r for r in negated_roots if r in positive_claims and len(r) > 3]
    if contradictions:
        issues.append(f"Possible self-contradiction: negation of earlier term(s) ({', '.join(contradictions[:3])}).")

    return {
        "status": "ok",
        "argument": argument,
        "valid": len(issues) == 0,
        "issues": issues,
        "verdict": "Heuristic check only — LLM unavailable." if not issues else f"Found {len(issues)} potential issue(s).",
        "method": "heuristic"
    }
