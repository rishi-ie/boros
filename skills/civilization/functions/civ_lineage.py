"""civ_lineage — Read lineage and diff two instances."""

import json
from pathlib import Path


def civ_lineage_read(params: dict, kernel=None) -> dict:
    """Read this instance's lineage record.

    Returns:
        identity: instance_id, parents, birth_type, generation
        events: list of lineage events (boot, fork_child, breed_child)
        gene_count: total genes in genome
        current_scores: latest high-water marks
    """
    boros_root = Path(kernel.boros_root) if kernel else Path(".")

    # Read lineage
    lineage_file = boros_root / "lineage.json"
    lineage = {"entries": []}
    if lineage_file.exists():
        try:
            lineage = json.loads(lineage_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            lineage = {"entries": []}

    # Read identity
    identity_file = boros_root / "identity.json"
    identity = {}
    if identity_file.exists():
        try:
            identity = json.loads(identity_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Count genes
    gene_count = 0
    genome_file = boros_root / "genome.jsonl"
    if genome_file.exists():
        try:
            with open(genome_file, "r", encoding="utf-8") as f:
                gene_count = sum(1 for line in f if line.strip())
        except OSError:
            pass

    # Read current scores
    hw_file = boros_root / "skills" / "eval-bridge" / "state" / "high_water_marks.json"
    scores = {}
    if hw_file.exists():
        try:
            scores = json.loads(hw_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "status": "ok",
        "identity": {
            "instance_id": identity.get("instance_id", "unknown"),
            "origin_id": identity.get("origin_id", ""),
            "parents": identity.get("parents", []),
            "birth_type": identity.get("birth_type", "unknown"),
            "generation": identity.get("generation", 0),
            "born_at": identity.get("born_at", ""),
            "world_model_hash": identity.get("world_model_hash", ""),
        },
        "events": lineage.get("entries", []),
        "gene_count": gene_count,
        "current_scores": scores,
    }


def civ_lineage_diff(params: dict, kernel=None) -> dict:
    """Compare this Boros instance with another.

    Params:
        other_path: path to the other Boros instance root directory

    Returns:
        self_identity, other_identity,
        common_origin (shared origin_id or None),
        shared_genes (gene_ids present in both),
        unique_genes_self, unique_genes_other,
        score_comparison, world_model_diff
    """
    boros_root = Path(kernel.boros_root) if kernel else Path(".")
    other_path = Path(params.get("other_path", ""))

    if not other_path.exists():
        return {"status": "error", "message": f"Other instance not found: {other_path}"}

    # Read self identity + genome
    self_identity = _read_identity(boros_root)
    other_identity = _read_identity(other_path)

    self_genes = _read_gene_ids(boros_root)
    other_genes = _read_gene_ids(other_path)

    # Find common origin
    common_origin = None
    if self_identity.get("origin_id") and self_identity["origin_id"] == other_identity.get("origin_id"):
        common_origin = self_identity["origin_id"]

    # Compute gene overlap
    shared = self_genes & other_genes
    unique_self = self_genes - other_genes
    unique_other = other_genes - self_genes

    # Score comparison
    self_scores = _read_scores(boros_root)
    other_scores = _read_scores(other_path)

    # World model diff
    self_wm_hash = self_identity.get("world_model_hash", "")
    other_wm_hash = other_identity.get("world_model_hash", "")
    self_wm_cats = _read_world_model_categories(boros_root)
    other_wm_cats = _read_world_model_categories(other_path)

    return {
        "status": "ok",
        "self_identity": self_identity,
        "other_identity": other_identity,
        "common_origin": common_origin,
        "shared_genes": len(shared),
        "unique_genes_self": len(unique_self),
        "unique_genes_other": len(unique_other),
        "score_comparison": {
            "self": self_scores,
            "other": other_scores,
        },
        "world_model_diff": {
            "same_hash": self_wm_hash == other_wm_hash,
            "self_categories": list(self_wm_cats),
            "other_categories": list(other_wm_cats),
            "shared_categories": list(self_wm_cats & other_wm_cats),
            "unique_self_categories": list(self_wm_cats - other_wm_cats),
            "unique_other_categories": list(other_wm_cats - self_wm_cats),
        },
    }


# ── Helpers ──────────────────────────────────────────

def _read_identity(boros_root: Path) -> dict:
    identity_file = boros_root / "identity.json"
    if identity_file.exists():
        try:
            return json.loads(identity_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _read_gene_ids(boros_root: Path) -> set:
    genome_file = boros_root / "genome.jsonl"
    gene_ids = set()
    if genome_file.exists():
        try:
            with open(genome_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        gene = json.loads(line)
                        gid = gene.get("gene_id")
                        if gid:
                            gene_ids.add(gid)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
    return gene_ids


def _read_scores(boros_root: Path) -> dict:
    hw_file = boros_root / "skills" / "eval-bridge" / "state" / "high_water_marks.json"
    if hw_file.exists():
        try:
            return json.loads(hw_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _read_world_model_categories(boros_root: Path) -> set:
    wm_file = boros_root / "world_model.json"
    if wm_file.exists():
        try:
            wm = json.loads(wm_file.read_text(encoding="utf-8"))
            return set(wm.get("categories", {}).keys())
        except (json.JSONDecodeError, OSError):
            pass
    return set()
