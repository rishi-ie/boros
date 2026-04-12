"""civ_heartbeat — Write a heartbeat broadcast with current instance state."""

import json
import datetime
from pathlib import Path
from ._internal.identity_utils import compute_world_model_hash


def civ_heartbeat(params: dict, kernel=None) -> dict:
    """Write a heartbeat broadcast — compact summary of this instance's state.

    Called at the end of every evolution cycle by loop_end_cycle.
    Written to heartbeat.json in the boros root.

    Params:
        cycle: int — current cycle number
        scores: dict — current scores by category
        last_outcome: str — outcome of last mutation
        last_delta: float — score delta of last mutation
        last_category: str — category of last mutation

    Returns:
        status, heartbeat data
    """
    boros_root = Path(kernel.boros_root) if kernel else Path(".")

    # Read identity
    identity_file = boros_root / "identity.json"
    identity = {}
    if identity_file.exists():
        try:
            identity = json.loads(identity_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    if not identity.get("instance_id"):
        return {"status": "skipped", "message": "No identity — heartbeat skipped."}

    # Read current mode from loop state
    mode = "evolution"
    state_file = boros_root / "session" / "loop_state.json"
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            mode = state.get("agent_state", state.get("mode", "evolution"))
        except (json.JSONDecodeError, OSError):
            pass

    # Read world model categories
    wm_categories = []
    wm_file = boros_root / "world_model.json"
    if wm_file.exists():
        try:
            wm = json.loads(wm_file.read_text(encoding="utf-8"))
            wm_categories = list(wm.get("categories", {}).keys())
        except (json.JSONDecodeError, OSError):
            pass

    # Count genes by origin
    genes_total = 0
    genes_evolved = 0
    genes_inherited = 0
    genes_bred = 0
    genome_file = boros_root / "genome.jsonl"
    if genome_file.exists():
        try:
            with open(genome_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        gene = json.loads(line)
                        genes_total += 1
                        origin = gene.get("origin", "evolved")
                        if origin == "evolved":
                            genes_evolved += 1
                        elif origin == "inherited":
                            genes_inherited += 1
                        elif origin == "bred":
                            genes_bred += 1
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass

    # Read children from lineage
    children = []
    lineage_file = boros_root / "lineage.json"
    if lineage_file.exists():
        try:
            lineage = json.loads(lineage_file.read_text(encoding="utf-8"))
            for entry in lineage.get("entries", []):
                if entry.get("event") in ("fork_child", "breed_child"):
                    child_id = entry.get("child_id")
                    if child_id:
                        children.append(child_id)
        except (json.JSONDecodeError, OSError):
            pass

    # Read last gene for last_mutation info
    last_mutation = None
    if genome_file.exists():
        try:
            with open(genome_file, "r", encoding="utf-8") as f:
                last_line = None
                for line in f:
                    if line.strip():
                        last_line = line.strip()
                if last_line:
                    last_gene = json.loads(last_line)
                    last_mutation = {
                        "gene_id": last_gene.get("gene_id"),
                        "category": last_gene.get("category"),
                        "outcome": "improved",  # only improved mutations become genes
                        "delta": last_gene.get("score_delta"),
                    }
        except (json.JSONDecodeError, OSError):
            pass

    # Override with params if provided (more current than last gene)
    scores = params.get("scores", {})
    cycle = params.get("cycle", 0)
    last_outcome = params.get("last_outcome")
    last_delta = params.get("last_delta")
    last_category = params.get("last_category")

    if last_outcome and last_category:
        last_mutation = {
            "gene_id": None,  # Not yet recorded as gene at this point
            "category": last_category,
            "outcome": last_outcome,
            "delta": last_delta,
        }

    heartbeat = {
        "instance_id": identity.get("instance_id"),
        "parents": identity.get("parents", []),
        "birth_type": identity.get("birth_type", "genesis"),
        "generation": identity.get("generation", 0),
        "cycle": cycle,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "mode": mode,
        "world_model_hash": compute_world_model_hash(boros_root),
        "world_model_categories": wm_categories,
        "scores": scores,
        "genes_total": genes_total,
        "genes_evolved": genes_evolved,
        "genes_inherited": genes_inherited,
        "genes_bred": genes_bred,
        "children": children,
        "last_mutation": last_mutation,
    }

    # Write heartbeat
    heartbeat_file = boros_root / "heartbeat.json"
    try:
        heartbeat_file.write_text(json.dumps(heartbeat, indent=2), encoding="utf-8")
    except OSError as e:
        return {"status": "error", "message": f"Failed to write heartbeat: {e}"}

    return {"status": "ok", "heartbeat": heartbeat}
