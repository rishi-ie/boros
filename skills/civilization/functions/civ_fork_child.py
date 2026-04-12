"""civ_fork_child — Handle identity + genome + lineage for a fork operation."""

import json
import datetime
import shutil
from pathlib import Path
from ._internal.identity_utils import generate_instance_id


def civ_fork_child(params: dict, kernel=None) -> dict:
    """Handle the civilization layer of a fork.

    Called by the director interface when the 'fork' command is issued.
    This does NOT create the child directory or copy code — that's the caller's job.
    This function:
      1. Generates child instance_id
      2. Writes identity_seed.json (child reads this on first boot)
      3. Records fork_child event in parent's lineage.json
      4. Prepares genome inheritance data
      5. Returns child identity info for display

    The caller (director interface or external breeder) is responsible for
    actually cloning the codebase and placing identity_seed.json + genome.jsonl
    in the child directory.

    Returns:
        child_id, child_generation, identity_seed, genome_stats
    """
    boros_root = Path(kernel.boros_root) if kernel else Path(".")

    # Read parent identity
    identity_file = boros_root / "identity.json"
    if not identity_file.exists():
        return {"status": "error", "message": "No identity.json — cannot fork without identity."}

    try:
        parent_identity = json.loads(identity_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {"status": "error", "message": f"Failed to read identity: {e}"}

    parent_id = parent_identity["instance_id"]
    parent_generation = parent_identity.get("generation", 0)
    child_id = generate_instance_id()
    child_generation = parent_generation + 1

    # Read parent scores for the lineage event
    hw_file = boros_root / "skills" / "eval-bridge" / "state" / "high_water_marks.json"
    parent_scores = {}
    if hw_file.exists():
        try:
            parent_scores = json.loads(hw_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Count parent genes
    gene_count = 0
    genome_file = boros_root / "genome.jsonl"
    if genome_file.exists():
        try:
            with open(genome_file, "r", encoding="utf-8") as f:
                gene_count = sum(1 for line in f if line.strip())
        except OSError:
            pass

    # Prepare identity seed for the child
    identity_seed = {
        "parent_instance_id": parent_id,
        "origin_id": parent_identity.get("origin_id", parent_id),
        "parents": [
            {
                "instance_id": parent_id,
                "generation": parent_generation,
                "scores": parent_scores,
            }
        ],
        "birth_type": "fork",
        "generation": child_generation,
    }

    # Write identity_seed.json in parent's directory
    # The caller copies this to the child directory during the fork/clone process
    seed_file = boros_root / "identity_seed.json"
    seed_file.write_text(json.dumps(identity_seed, indent=2), encoding="utf-8")

    # Prepare inherited genome
    # Write a copy of the genome with all genes marked as "inherited"
    inherited_genome_file = boros_root / "genome_inherited.jsonl"
    if genome_file.exists():
        try:
            with open(genome_file, "r", encoding="utf-8") as src, \
                 open(inherited_genome_file, "w", encoding="utf-8") as dst:
                for line in src:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        gene = json.loads(line)
                        gene["origin"] = "inherited"
                        gene["inherited_from"] = parent_id
                        dst.write(json.dumps(gene, default=str) + "\n")
                    except json.JSONDecodeError:
                        continue
        except OSError as e:
            print(f"[civilization] WARNING: Failed to prepare inherited genome: {e}")

    # Record fork_child event in parent's lineage
    lineage_file = boros_root / "lineage.json"
    lineage = {"entries": []}
    if lineage_file.exists():
        try:
            lineage = json.loads(lineage_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            lineage = {"entries": []}

    if "entries" not in lineage:
        lineage["entries"] = []

    # Read current cycle from loop state
    cycle = 0
    state_file = boros_root / "session" / "loop_state.json"
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            cycle = state.get("cycle", 0)
        except (json.JSONDecodeError, OSError):
            pass

    lineage["entries"].append({
        "event": "fork_child",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "cycle": cycle,
        "child_id": child_id,
        "child_generation": child_generation,
        "scores_at_event": parent_scores,
        "genes_count": gene_count,
    })

    lineage_file.write_text(json.dumps(lineage, indent=2), encoding="utf-8")

    print(f"[civilization] Fork prepared: child={child_id}, gen={child_generation}, genes={gene_count}")

    return {
        "status": "ok",
        "child_id": child_id,
        "child_generation": child_generation,
        "parent_id": parent_id,
        "identity_seed_written": True,
        "inherited_genome_written": genome_file.exists(),
        "gene_count": gene_count,
    }
