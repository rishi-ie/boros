import json
import re

def reason_generate_plan(params: dict, kernel=None) -> dict:
    """
    Decomposes a complex problem into a structured, step-by-step plan.

    This function takes a high-level problem statement and generates a detailed plan
    as a JSON object. The plan includes a list of sequential steps, specifying the
    tool to be used for each step and the expected artifact (output) of that step.

    Args:
        params (dict): A dictionary containing the problem description.
                       Expected key: "problem" (str).
        kernel: The Boros kernel object, providing access to core services
                like the LLM.

    Returns:
        dict: A dictionary containing the status of the operation and the
              generated plan. On success, {"status": "ok", "plan": {...}}.
              On error, {"status": "error", "message": "..."}.
    """
    problem = params.get("problem", "")
    if not problem:
        return {"status": "error", "message": "Parameter 'problem' is required."}

    if not kernel or not hasattr(kernel, "evolution_llm"):
        return {"status": "error", "message": "Evolution LLM is not available in the kernel."}

    prompt = f"""
You are the Boros reasoning cortex. Your task is to create a structured, step-by-step execution plan to solve a given problem.

The plan must be a valid JSON object with a single key "plan", which is an array of steps. Each step in the array must be a JSON object with three keys:
1. "step" (integer): The sequential step number, starting from 1.
2. "action" (string): A concise description of the task to be performed in this step.
3. "tool" (string): The specific tool to be used (e.g., "tool_terminal", "tool_file_edit_diff", "research_search_engine"). If no tool is needed (e.g., for pure reasoning), use "reasoning".
4. "expected_artifact" (string): A description of the concrete output or result of this step (e.g., "A file named 'solution.py'", "A list of relevant URLs", "A verified algorithm").

Problem: "{problem}"

Generate the JSON plan now.
"""

    try:
        response = kernel.evolution_llm.complete(
            [{"role": "user", "content": prompt}],
            system="You are a meticulous planning AI. Output ONLY the valid JSON plan object."
        )
        
        # Extract the JSON part from the response text
        text_content = "".join(b.get("text", "") for b in response.get("content", []) if b.get("type") == "text")
        
        # Safely extract the outermost JSON object (handles nested braces)
        start = text_content.find("{")
        plan_json = None
        if start != -1:
            for end in range(len(text_content), start, -1):
                try:
                    plan_json = json.loads(text_content[start:end])
                    break
                except json.JSONDecodeError:
                    continue

        if plan_json is None:
            return {"status": "error", "message": "No valid JSON object found in the LLM response.", "raw_response": text_content}

        # Basic validation of the generated plan structure
        if "plan" not in plan_json or not isinstance(plan_json["plan"], list):
            return {"status": "error", "message": "Generated JSON is missing the root 'plan' array.", "raw_plan": plan_json}
        
        if not plan_json["plan"]:
            return {"status": "error", "message": "Generated plan is empty. It must contain at least one step.", "raw_plan": plan_json}

        required_step_keys = ["step", "action", "tool", "expected_artifact"]
        for i, step in enumerate(plan_json["plan"]):
            if not isinstance(step, dict):
                return {"status": "error", "message": f"Plan step {i+1} is not a valid object.", "raw_plan": plan_json}
            for key in required_step_keys:
                if key not in step:
                    return {"status": "error", "message": f"Plan step {i+1} is missing the required key: '{key}'.", "raw_plan": plan_json}

        return {"status": "ok", "plan": plan_json}

    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"Failed to decode LLM response as JSON: {e}", "raw_response": text_content}
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred during plan generation: {e}"}
