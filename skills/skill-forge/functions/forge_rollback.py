
import os, json, shutil
def forge_rollback(params: dict, kernel=None) -> dict:
    """Rollback a skill to a previous snapshot."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    skill_name = params.get("target", params.get("skill_name", ""))
    snapshot_id = params.get("snapshot_id", "")

    if not skill_name or not snapshot_id:
        return {"status": "error", "message": "skill_name and snapshot_id required"}

    snap_dir = os.path.join(boros_dir, "snapshots", snapshot_id, "functions_backup")
    target_dir = os.path.join(boros_dir, "skills", skill_name, "functions")

    if not os.path.isdir(snap_dir):
        return {"status": "error", "message": f"Snapshot backup not found: {snap_dir}"}

    restored = []
    for fname in os.listdir(snap_dir):
        shutil.copy2(os.path.join(snap_dir, fname), os.path.join(target_dir, fname))
        restored.append(fname)

    return {"status": "ok", "message": f"Restored {len(restored)} files for {skill_name}", "files": restored}
