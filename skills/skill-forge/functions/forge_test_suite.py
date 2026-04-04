
import subprocess, os
def forge_test_suite(params: dict, kernel=None) -> dict:
    """Run the test suite for a skill."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    skill_name = params.get("target", params.get("skill_name", ""))
    if not skill_name:
        return {"status": "error", "message": "skill_name required"}

    tests_dir = os.path.join(boros_dir, "skills", skill_name, "tests")
    if not os.path.isdir(tests_dir) or not os.listdir(tests_dir):
        return {"status": "ok", "message": "No tests found for this skill.", "passed": True, "output": ""}

    try:
        result = subprocess.run(
            ["python", "-m", "pytest", tests_dir, "-v", "--tb=short"],
            capture_output=True, text=True, timeout=60,
            cwd=str(kernel.boros_root) if kernel else "."
        )
        passed = result.returncode == 0
        return {
            "status": "ok",
            "passed": passed,
            "returncode": result.returncode,
            "stdout": result.stdout[:3000],
            "stderr": result.stderr[:1000]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
