import json

def reason_decompose(params: dict, kernel=None) -> dict:
    problem = params.get("problem", "")
    if not problem:
        return {"status": "error", "message": "problem required"}
        
    if kernel and hasattr(kernel, "evolution_llm"):
        prompt = (f"You are the Boros reasoning cortex. Your task is to decompose a complex problem into a logical, actionable sequence of smaller, manageable sub-problems or steps. Think step-by-step to identify the key components, required information, and necessary actions.\n\n"
                  f"Problem: {problem}\n\n"
                  f"Provide your response ONLY as a valid JSON array of strings, where each string is a clearly defined, actionable step. If a step involves a direct tool call, ensure it is a fully formed tool call (e.g., `tool_terminal(command=\"dir\")`). Otherwise, describe the step simply. Prioritize simple, directly executable steps.\n\n"
                  f"Problem: {problem}\n\n"
                  f"Example: [\"tool_terminal(command=\"dir\")\", \"Read 'config.json'\"]")
        try:
            res = kernel.evolution_llm.complete([{"role": "user", "content": prompt}], system="You are the reasoning cortex. Decompose the problem into actionable steps, including fully formed tool calls when appropriate.")
            text = "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text")
            import re
            match = re.search(r'\[.*\]', text, flags=re.DOTALL)
            if not match:
                raise ValueError(f"No valid JSON array found in LLM response: {text}")
            sub_problems = json.loads(match.group())
            if not isinstance(sub_problems, list) or not all(isinstance(s, str) for s in sub_problems):
                raise ValueError(f"LLM response is not a valid JSON array of strings: {sub_problems}")
            
            return {"status": "ok", "sub_problems": sub_problems, "count": len(sub_problems)}
        except (json.JSONDecodeError, ValueError) as e:
            return {"status": "error", "message": f"LLM response processing failed: {e}", "raw_response": text}
        except Exception as e:
            return {"status": "error", "message": f"An unexpected error occurred during LLM decomposition: {e}"}
            
    # Fallback
    parts = [s.strip() for s in problem.split(".") if s.strip()]
    return {"status": "ok", "sub_problems": parts, "count": len(parts), "note": "Heuristic fallback."}
