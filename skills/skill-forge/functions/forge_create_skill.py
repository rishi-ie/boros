
import os, json, datetime
def forge_create_skill(params: dict, kernel=None) -> dict:
    """Scaffold a new skill directory with standard structure."""
    boros_dir = str(kernel.boros_root) if kernel else __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))))
    skill_name = params.get("skill_name", "")
    description = params.get("description", "")
    functions = params.get("functions", [])
    if not skill_name:
        return {"status": "error", "message": "skill_name required"}
    skill_dir = os.path.join(boros_dir, "skills", skill_name)
    if os.path.exists(skill_dir):
        return {"status": "error", "message": f"Skill '{skill_name}' already exists"}
    for subdir in ["functions", "state", "tests", "metrics", "snapshots"]:
        os.makedirs(os.path.join(skill_dir, subdir), exist_ok=True)
    with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
        f.write(f"# {skill_name}\n\n{description}\n")
    with open(os.path.join(skill_dir, "skill.json"), "w") as f:
        json.dump({"name": skill_name, "version": "0.1.0", "provided_functions": functions}, f, indent=2)
    with open(os.path.join(skill_dir, "changelog.md"), "w") as f:
        f.write(f"# Changelog\n- Created: {datetime.datetime.utcnow().isoformat()}Z\n")
    init_imports = []
    for fn in functions:
        with open(os.path.join(skill_dir, "functions", f"{fn}.py"), "w") as f:
            f.write(f"def {fn}(params: dict, kernel=None) -> dict:\n    return {{'status': 'ok'}}\n")
        init_imports.append(f"from .{fn} import {fn}")
    with open(os.path.join(skill_dir, "functions", "__init__.py"), "w") as f:
        f.write("\n".join(init_imports) + "\n")
        
    with open(os.path.join(skill_dir, "tests", "test_basic.py"), "w") as f:
        f.write("def test_health_check():\n    assert True\n")

    # ── UPDATE MANIFEST.JSON ──
    manifest_path = os.path.join(boros_dir, "manifest.json")
    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        manifest["skills"][skill_name] = {
            "path": f"skills/{skill_name}",
            "type": "demand",
            "dependencies": [],
            "provided_functions": functions
        }
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
    except Exception as e:
        return {"status": "partial", "message": f"Skill created but manifest update failed: {e}", "path": skill_dir}

    # ── HOT-LOAD into live kernel registry ──
    if kernel:
        try:
            import importlib
            module_path = f"skills.{skill_name}.functions"
            module = importlib.import_module(module_path)
            for fn in functions:
                if hasattr(module, fn):
                    kernel.registry[fn] = getattr(module, fn)
            kernel.manifest = manifest
        except Exception as e:
            return {"status": "partial", "message": f"Skill created + manifest updated, but hot-load failed: {e}", "path": skill_dir}

    return {"status": "ok", "path": skill_dir, "message": f"Skill {skill_name} scaffolded, manifest updated, registry loaded."}

