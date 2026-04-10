import os
import json
import datetime

def generate_evaluation_artifact(params: dict, kernel=None) -> dict:
    """Generates an artifact file in the eval-generator shared artifacts directory.

    This function takes a dictionary `params` with keys 'content' (dict) and
    'artifact_name' (str), and writes the content as a JSON file in the
    `eval-generator/shared/artifacts` directory. This is intended to be used
    by skills that need to produce file-based artifacts for evaluation,
    especially when internal functions are modified and their generative
    depth needs to be assessed.
    """
    content = params.get("content", {})
    artifact_name = params.get("artifact_name", "artifact")
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    artifacts_dir = os.path.join(boros_dir, "eval-generator", "shared", "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)

    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{artifact_name}_{timestamp}.json"
    artifact_path = os.path.join(artifacts_dir, filename)

    try:
        with open(artifact_path, "w") as f:
            json.dump(content, f, indent=2)
        return {"status": "ok", "message": f"Artifact '{filename}' created successfully at {artifact_path}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to create artifact: {e}"}
 
