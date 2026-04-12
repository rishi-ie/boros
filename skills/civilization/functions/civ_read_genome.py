"""civ_read_genome — Read the genome (all genes this instance has accumulated)."""

import json
from pathlib import Path


def civ_read_genome(params: dict, kernel=None) -> dict:
    """Read the genome — all genes this instance has accumulated.

    Params:
        filter_origin: optional — "evolved" | "inherited" | "bred"
        filter_category: optional — filter by world model category
        limit: optional — max genes to return (most recent first)

    Returns:
        genes: list of gene records (most recent first)
        total: total gene count (before filtering)
        stats: {evolved: N, inherited: N, bred: N}
    """
    boros_root = Path(kernel.boros_root) if kernel else Path(".")

    genome_file = boros_root / "genome.jsonl"
    if not genome_file.exists():
        return {
            "status": "ok",
            "genes": [],
            "total": 0,
            "stats": {"evolved": 0, "inherited": 0, "bred": 0},
        }

    # Read all genes
    all_genes = []
    try:
        with open(genome_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    all_genes.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError as e:
        return {"status": "error", "message": f"Failed to read genome: {e}"}

    total = len(all_genes)

    # Compute stats
    stats = {"evolved": 0, "inherited": 0, "bred": 0}
    for gene in all_genes:
        origin = gene.get("origin", "evolved")
        if origin in stats:
            stats[origin] += 1

    # Apply filters
    filtered = all_genes
    filter_origin = params.get("filter_origin")
    if filter_origin:
        filtered = [g for g in filtered if g.get("origin") == filter_origin]

    filter_category = params.get("filter_category")
    if filter_category:
        filtered = [g for g in filtered if g.get("category") == filter_category]

    # Most recent first
    filtered.reverse()

    # Apply limit
    limit = params.get("limit")
    if limit and isinstance(limit, int) and limit > 0:
        filtered = filtered[:limit]

    return {
        "status": "ok",
        "genes": filtered,
        "total": total,
        "stats": stats,
    }
