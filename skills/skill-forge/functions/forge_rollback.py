
import os, json, shutil
def forge_rollback(params: dict, kernel=None) -> dict:
    """Rollback a skill to a previous snapshot."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    skill_name = params.get("target", params.get("skill_name", ""))
    snapshot_id = params.get("snapshot_id", "")

    # Normalize: if a full path was passed (e.g. "skills/memory/functions/foo.py"), extract skill name
    if skill_name:
        normalized = skill_name.replace("\\", "/")
        parts = normalized.split("/")
        if len(parts) >= 2 and parts[0] == "skills":
            skill_name = parts[1]

    if not skill_name or not snapshot_id:
        return {"status": "error", "message": "skill_name and snapshot_id required"}

    snap_root = os.path.join(boros_dir, "snapshots", snapshot_id)
    func_backup_dir = os.path.join(snap_root, "functions_backup")
    target_dir = os.path.join(boros_dir, "skills", skill_name, "functions")

    if not os.path.isdir(func_backup_dir):
        return {"status": "error", "message": f"Snapshot backup not found: {func_backup_dir}"}

    restored = []
    for fname in os.listdir(func_backup_dir):
        shutil.copy2(os.path.join(func_backup_dir, fname), os.path.join(target_dir, fname))
        restored.append(fname)

    # Restore SKILL.md if it was included in the snapshot
    skill_md_backup = os.path.join(snap_root, "SKILL.md")
    if os.path.exists(skill_md_backup):
        skill_md_target = os.path.join(boros_dir, "skills", skill_name, "SKILL.md")
        shutil.copy2(skill_md_backup, skill_md_target)
        restored.append("SKILL.md")

    # Hot-reload the skill so the restored code is live immediately (not just on disk)
    if kernel and hasattr(kernel, "reload_skill"):
        try:
            kernel.reload_skill(skill_name)
        except Exception as e:
            return {"status": "ok", "message": f"Restored {len(restored)} files for {skill_name} but hot-reload failed: {e}", "files": restored}

    return {"status": "ok", "message": f"Restored {len(restored)} files for {skill_name} and hot-reloaded.", "files": restored}
