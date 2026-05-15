"""
Version Control — full git-like history for Boros.
Every change is recorded. Any state can be diffed and rolled back.
"""

from __future__ import annotations
import json
import shutil
import datetime
import uuid
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Snapshot:
    id: str
    timestamp: str
    label: str
    cycle: int
    scores: dict
    changed_files: list[str]
    commit_message: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "label": self.label,
            "cycle": self.cycle,
            "scores": self.scores,
            "changed_files": self.changed_files,
            "commit_message": self.commit_message,
        }


class VersionControl:
    """
    Full git-like version control for Boros.

    Features:
    - Snapshot every evolution cycle
    - Diff between any two snapshots
    - Rollback to any snapshot
    - Bisect to find which change broke something
    - Named tags
    """

    TRACKED_FILES = [
        "skills",
        "kernel.py",
        "agent_loop.py",
        "world_model.json",
        "manifest.json",
        "config.json",
    ]

    def __init__(self, boros_root: Path | None = None):
        self.boros_root = boros_root or Path(__file__).parent.parent.parent
        self.snapshots_dir = self.boros_root / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        self.index_file = self.boros_root / "session" / "version_index.json"
        self.index = self._load_index()

    def _load_index(self) -> dict:
        if self.index_file.exists():
            return json.loads(self.index_file.read_text())
        return {"snapshots": [], "current": None, "tags": {}}

    def _save_index(self) -> None:
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        self.index_file.write_text(json.dumps(self.index, indent=2))

    def snapshot(
        self,
        label: str = "",
        cycle: int = 0,
        scores: dict | None = None,
        commit_message: str = "",
    ) -> str:
        """
        Create a full state snapshot.
        Returns snapshot ID.
        """
        snapshot_id = f"snap-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

        changed_files = self._find_changed_files()
        scores = scores or {}

        snap_meta = Snapshot(
            id=snapshot_id,
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            label=label or snapshot_id,
            cycle=cycle,
            scores=scores,
            changed_files=changed_files,
            commit_message=commit_message or f"Auto-snapshot: {label}",
        )

        snap_file = self.snapshots_dir / f"{snapshot_id}.json"
        snap_file.write_text(json.dumps(snap_meta.to_dict(), indent=2))

        # Copy tracked files into snapshot
        snap_state_dir = self.snapshots_dir / snapshot_id
        snap_state_dir.mkdir(exist_ok=True)

        for rel_path in self.TRACKED_FILES:
            src = self.boros_root / rel_path
            dst = snap_state_dir / rel_path
            if src.exists():
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)

        self.index["snapshots"].append(snapshot_id)
        self.index["current"] = snapshot_id
        self._save_index()

        return snapshot_id

    def _find_changed_files(self) -> list[str]:
        if not self.index["snapshots"]:
            return self.TRACKED_FILES[:]

        last_snap = self.index["snapshots"][-1]
        last_snap_dir = self.snapshots_dir / last_snap

        changed = []
        for rel_path in self.TRACKED_FILES:
            src = self.boros_root / rel_path
            dst = last_snap_dir / rel_path

            if not src.exists():
                continue

            if src.is_dir():
                if not dst.exists() or not self._dirs_equal(src, dst):
                    changed.append(rel_path)
            else:
                if not dst.exists() or src.read_bytes() != dst.read_bytes():
                    changed.append(rel_path)

        return changed

    def _dirs_equal(self, a: Path, b: Path) -> bool:
        import filecmp
        return filecmp.dircmp(a, b).left_only == []

    def diff(self, from_id: str, to_id: str) -> dict:
        """Show diff between two snapshots."""
        from_dir = self.snapshots_dir / from_id
        to_dir = self.snapshots_dir / to_id

        if not from_dir.exists() or not to_dir.exists():
            return {"error": "Snapshot not found"}

        diff_result = {}
        for rel_path in self.TRACKED_FILES:
            from_file = from_dir / rel_path
            to_file = to_dir / rel_path

            if not from_file.exists() and not to_file.exists():
                continue

            if not from_file.exists():
                diff_result[rel_path] = {
                    "status": "added",
                    "content": to_file.read_text(),
                }
            elif not to_file.exists():
                diff_result[rel_path] = {
                    "status": "deleted",
                    "content": from_file.read_text(),
                }
            else:
                import difflib

                diff = list(
                    difflib.unified_diff(
                        from_file.read_text().splitlines(),
                        to_file.read_text().splitlines(),
                        fromfile=str(from_file),
                        tofile=str(to_file),
                        lineterm="",
                    )
                )
                if diff:
                    diff_result[rel_path] = {
                        "status": "modified",
                        "diff": "\n".join(diff),
                    }

        return diff_result

    def rollback(self, snapshot_id: str) -> dict:
        """Rollback to a specific snapshot."""
        snap_dir = self.snapshots_dir / snapshot_id
        if not snap_dir.exists():
            return {"error": f"Snapshot '{snapshot_id}' not found"}

        restored = []
        for rel_path in self.TRACKED_FILES:
            snap_file = snap_dir / rel_path
            dst = self.boros_root / rel_path

            if not snap_file.exists():
                continue

            if snap_file.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(snap_file, dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(snap_file, dst)

            restored.append(rel_path)

        self.index["current"] = snapshot_id
        self._save_index()

        return {"restored": restored, "snapshot": snapshot_id}

    def bisect(
        self, bad_id: str, good_id: str, test_func: callable
    ) -> str:
        """Binary search for which snapshot caused a regression."""
        snapshots = self.index["snapshots"]
        try:
            bad_idx = snapshots.index(bad_id)
            good_idx = snapshots.index(good_id)
        except ValueError:
            return "error: snapshot not found"

        if good_idx > bad_idx:
            good_idx, bad_idx = bad_idx, good_idx

        while good_idx < bad_idx - 1:
            mid_idx = (good_idx + bad_idx) // 2
            mid_id = snapshots[mid_idx]
            result = test_func(mid_id)
            if result:
                good_idx = mid_idx
            else:
                bad_idx = mid_idx

        return snapshots[bad_idx]

    def log(self, limit: int = 50) -> list[dict]:
        """Show recent snapshot history."""
        logs = []
        for snap_id in reversed(self.index["snapshots"][-limit:]):
            snap_file = self.snapshots_dir / f"{snap_id}.json"
            if snap_file.exists():
                logs.append(json.loads(snap_file.read_text()))
        return logs

    def tag(self, snapshot_id: str, tag_name: str) -> None:
        """Tag a snapshot."""
        if "tags" not in self.index:
            self.index["tags"] = {}
        self.index["tags"][tag_name] = snapshot_id
        self._save_index()

    def get_tag(self, tag_name: str) -> str | None:
        """Get snapshot ID for a tag."""
        return self.index.get("tags", {}).get(tag_name)