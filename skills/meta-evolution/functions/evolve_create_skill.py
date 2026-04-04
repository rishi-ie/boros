
import os, json, uuid, datetime
def evolve_create_skill(params: dict, kernel=None) -> dict:
    """Create a brand new skill with full directory structure."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    skill_name = params.get("skill_name", "")
    description = params.get("description", "")
    functions = params.get("functions", [])
    schemas_json = params.get("schemas_json", "[]")

    if not skill_name:
        return {"status": "error", "message": "skill_name required"}

    skill_dir = os.path.join(boros_dir, "skills", skill_name)
    if os.path.exists(skill_dir):
        return {"status": "error", "message": f"Skill {skill_name} already exists"}

    # Create directory structure
    for subdir in ["functions", "state", "tests", "metrics", "snapshots"]:
        os.makedirs(os.path.join(skill_dir, subdir), exist_ok=True)

    # Create SKILL.md
    with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
        f.write(f"# {skill_name}\n\n{description}\n")

    # Create skill.json
    with open(os.path.join(skill_dir, "skill.json"), "w") as f:
        json.dump({"name": skill_name, "description": description, "version": "0.1.0", "provided_functions": functions}, f, indent=2)

    # Create changelog
    with open(os.path.join(skill_dir, "changelog.md"), "w") as f:
        f.write(f"# Changelog\n\n- {datetime.datetime.utcnow().isoformat()}Z: Created\n")

    # Create stub function files
    init_imports = []
    for func_name in functions:
        with open(os.path.join(skill_dir, "functions", f"{func_name}.py"), "w") as f:
            f.write(f"def {func_name}(params: dict, kernel=None) -> dict:\n    return {{'status': 'ok'}}\n")
        init_imports.append(f"from .{func_name} import {func_name}")

    with open(os.path.join(skill_dir, "functions", "__init__.py"), "w") as f:
        f.write("\n".join(init_imports) + "\n")

    # ── UPDATE MANIFEST.JSON so the kernel loads this skill on next boot ──
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
            module_path = f"boros.skills.{skill_name}.functions"
            module = importlib.import_module(module_path)
            for func_name in functions:
                if hasattr(module, func_name):
                    kernel.registry[func_name] = getattr(module, func_name)
            # Update kernel's manifest reference
            kernel.manifest = manifest
        except Exception as e:
            return {"status": "partial", "message": f"Skill created + manifest updated, but hot-load failed: {e}", "path": skill_dir}

    # ── UPDATE tool_schemas.py mathematically ──
    try:
        schema_objects = json.loads(schemas_json) if isinstance(schemas_json, str) else schemas_json
        if schema_objects:
            schemas_path = os.path.join(boros_dir, "tool_schemas.py")
            with open(schemas_path, "r") as f:
                content = f.read()

            last_brace = content.rfind("}")
            if last_brace != -1:
                injection = f"\n    # ── Dynamic Skill: {skill_name} ──\n"
                for s in schema_objects:
                    name = s.get("name")
                    injection += f'    "{name}": {json.dumps(s)},\n'
                
                new_content = content[:last_brace] + injection + "}\n"
                with open(schemas_path, "w") as f:
                    f.write(new_content)
                
                # Active injection into runtime namespace
                import boros.tool_schemas
                import importlib
                importlib.reload(boros.tool_schemas)
                for s in schema_objects:
                    boros.tool_schemas.TOOL_SCHEMAS[s["name"]] = s

    except Exception as e:
        return {"status": "partial", "message": f"Skill created but failed to inject schemas into tool_schemas.py: {e}", "path": skill_dir}

    return {"status": "ok", "message": f"Skill {skill_name} created with {len(functions)} functions, manifest updated, registry loaded, and schemas injected.", "path": skill_dir}
