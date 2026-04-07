
import os, json, shutil, uuid, datetime
def forge_snapshot(params: dict, kernel=None) -> dict:
    """Create a restorable snapshot of a skill's current function files."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    skill_name_raw = params.get("target", params.get("skill_name", ""))
    if not skill_name_raw:
        return {"status": "error", "message": "target or skill_name required"}

    # Extract skill directory name even if a full path is passed
    skill_name = skill_name_raw.replace('\\', '/')
    if "/skills/" in skill_name:
        skill_name = skill_name.split("/skills/")[-1].split("/")[0]
    elif skill_name.startswith("skills/"):
        skill_name = skill_name.split("/")[1]
    elif "/" in skill_name:
        skill_name = skill_name.split("/")[0]
    else:
        skill_name = skill_name_raw

    func_dir = os.path.join(boros_dir, "skills", skill_name, "functions")
    if not os.path.isdir(func_dir):
        return {"status": "error", "message": f"Skill functions not found for target {skill_name_raw}: {func_dir}"}

    snapshot_id = f"snap-{uuid.uuid4().hex[:8]}"
    snap_dir = os.path.join(boros_dir, "snapshots", snapshot_id)
    backup_dir = os.path.join(snap_dir, "functions_backup")
    os.makedirs(backup_dir, exist_ok=True)

    # Copy all .py files
    files_copied = []
    for fname in os.listdir(func_dir):
        if fname.endswith(".py"):
            shutil.copy2(os.path.join(func_dir, fname), os.path.join(backup_dir, fname))
            files_copied.append(fname)

    # Also snapshot SKILL.md so forge_rollback can restore semantic edits too
    skill_md_src = os.path.join(boros_dir, "skills", skill_name, "SKILL.md")
    if os.path.exists(skill_md_src):
        shutil.copy2(skill_md_src, os.path.join(snap_dir, "SKILL.md"))

    # Write metadata
    with open(os.path.join(snap_dir, "snapshot_meta.json"), "w") as f:
        json.dump({
            "snapshot_id": snapshot_id,
            "skill_name": skill_name,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "files": files_copied,
            "has_skill_md": os.path.exists(skill_md_src)
        }, f, indent=2)

    # Persist snapshot_id into evolution_target.json so crash recovery can rollback
    target_file = os.path.join(boros_dir, "session", "evolution_target.json")
    if os.path.exists(target_file):
        try:
            with open(target_file) as f:
                target_data = json.load(f)
            target_data["snapshot_id"] = snapshot_id
            with open(target_file, "w") as f:
                json.dump(target_data, f, indent=2)
        except (json.JSONDecodeError, OSError):
            pass  # non-fatal — crash recovery just won't have the id

    return {"status": "ok", "snapshot_id": snapshot_id, "files_snapshotted": len(files_copied)}
