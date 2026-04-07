import json

def reason_decompose(params: dict, kernel=None) -> dict:
    problem = params.get("problem", "")
    if not problem:
        return {"status": "error", "message": "problem required"}
        
    if kernel and hasattr(kernel, "evolution_llm"):
        prompt = (
            f"You are the Boros reasoning cortex. Decompose this problem into a logical, "
            f"actionable sequence of smaller steps.\n\n"
            f"Problem: {problem}\n\n"
            f"Respond ONLY as a valid JSON array of strings, each a clearly defined actionable step.\n"
            f'Example: ["Inspect the target file", "Identify the failing function", "Apply the fix"]'
        )
        text = ""
        try:
            res = kernel.evolution_llm.complete(
                [{"role": "user", "content": prompt}],
                system="You are the reasoning cortex. Output only a JSON array of strings."
            )
            text = "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text")
            import re
            match = re.search(r'\[.*\]', text, flags=re.DOTALL)
            if not match:
                raise ValueError(f"No JSON array in LLM response: {text[:200]}")
            sub_problems = json.loads(match.group())
            if not isinstance(sub_problems, list) or not all(isinstance(s, str) for s in sub_problems):
                raise ValueError(f"Not a JSON array of strings: {sub_problems}")
            return {"status": "ok", "sub_problems": sub_problems, "count": len(sub_problems)}
        except (json.JSONDecodeError, ValueError) as e:
            return {"status": "error", "message": f"LLM response processing failed: {e}", "raw_response": text}
        except Exception as e:
            return {"status": "error", "message": f"Unexpected error during decomposition: {e}"}
            
    # Fallback
    parts = [s.strip() for s in problem.split(".") if s.strip()]
    return {"status": "ok", "sub_problems": parts, "count": len(parts), "note": "Heuristic fallback."}
