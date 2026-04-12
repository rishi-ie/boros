
import os, json, shutil
def evolve_rollback(params: dict, kernel=None) -> dict:
    """Rollback a skill to a previous snapshot."""
    boros_dir = str(kernel.boros_root) if kernel else __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))))
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

    # Restore function files from snapshot
    backup_dir = os.path.join(snap_dir, "functions_backup")
    files_restored = []
    if os.path.isdir(backup_dir):
        for fname in os.listdir(backup_dir):
            src = os.path.join(backup_dir, fname)
            dst = os.path.join(target_dir, fname)
            shutil.copy2(src, dst)
            files_restored.append(fname)

    # Also restore SKILL.md if it was snapshotted
    skill_md_snap = os.path.join(snap_dir, "SKILL.md")
    skill_md_dst  = os.path.join(boros_dir, "skills", skill_name, "SKILL.md")
    if os.path.exists(skill_md_snap):
        shutil.copy2(skill_md_snap, skill_md_dst)

    # Hot-reload the skill so the restored code is live immediately
    if kernel and hasattr(kernel, "reload_skill"):
        try:
            kernel.reload_skill(skill_name)
        except Exception as e:
            print(f"[evolve_rollback] WARNING: hot-reload failed after rollback: {e}")

    return {
        "status": "ok",
        "message": f"Rolled back {skill_name} to snapshot {snapshot_id}",
        "files_restored": files_restored
    }
