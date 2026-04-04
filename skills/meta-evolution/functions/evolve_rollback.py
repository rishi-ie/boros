
import os, json, shutil
def evolve_rollback(params: dict, kernel=None) -> dict:
    """Rollback a skill to a previous snapshot."""
    boros_dir = str(kernel.boros_root) if kernel else "boros"
    snapshot_id = params.get("snapshot_id", "")

    snap_dir = os.path.join(boros_dir, "snapshots", snapshot_id)
    if not os.path.isdir(snap_dir):
        return {"status": "error", "message": f"Snapshot {snapshot_id} not found"}

    # Read snapshot metadata
    meta_file = os.path.join(snap_dir, "snapshot_meta.json")
    if not os.path.exists(meta_file):
        return {"status": "error", "message": "Snapshot metadata missing"}

    with open(meta_file) as f:
        meta = json.load(f)

    skill_name = meta.get("skill_name", "")
    target_dir = os.path.join(boros_dir, "skills", skill_name, "functions")

    if not os.path.isdir(target_dir):
        return {"status": "error", "message": f"Skill functions dir not found: {target_dir}"}

    # Restore files from snapshot
    backup_dir = os.path.join(snap_dir, "functions_backup")
    if os.path.isdir(backup_dir):
        for fname in os.listdir(backup_dir):
            src = os.path.join(backup_dir, fname)
            dst = os.path.join(target_dir, fname)
            shutil.copy2(src, dst)

    return {"status": "ok", "message": f"Rolled back {skill_name} to snapshot {snapshot_id}", "files_restored": os.listdir(backup_dir) if os.path.isdir(backup_dir) else []}
