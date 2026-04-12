"""civ_record_gene — Record a successful mutation as a gene in the genome."""

import json
import hashlib
import datetime
from pathlib import Path


def civ_record_gene(params: dict, kernel=None) -> dict:
    """Record a successful mutation as a gene in the genome.

    Called by loop_end_cycle when outcome == 'improved'.
    Genes are append-only — they represent proven beneficial mutations.

    Params:
        cycle: int — evolution cycle number
        target_skill: str — skill that was modified
        target_file: str — file path that was modified
        approach: str — description of what was changed
        diff: str — raw diff content (code change)
        score_delta: float — score improvement
        score_before: dict — scores before mutation
        score_after: dict — scores after mutation
        proposal_id: str — linked proposal ID
        review_verdict: str — review board verdict

    Returns:
        status, gene_id, gene record
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

    instance_id = identity.get("instance_id", "unknown")
    generation = identity.get("generation", 0)

    # Generate gene_id from hash of instance + cycle + timestamp
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    cycle = params.get("cycle", 0)
    raw = f"{instance_id}:{cycle}:{timestamp}"
    gene_id = f"gene-{hashlib.sha256(raw.encode()).hexdigest()[:8]}"

    # Determine category from target_skill (usually matches world model category)
    target_skill = params.get("target_skill", "")
    category = target_skill  # In the current architecture, skill name == category

    gene = {
        "gene_id": gene_id,
        "instance_id": instance_id,
        "generation": generation,
        "cycle": cycle,
        "timestamp": timestamp,
        "origin": "evolved",
        "category": category,
        "target_skill": target_skill,
        "target_file": params.get("target_file", ""),
        "approach": params.get("approach", "")[:500],
        "diff": params.get("diff", ""),
        "score_delta": params.get("score_delta"),
        "score_before": params.get("score_before", {}),
        "score_after": params.get("score_after", {}),
        "review_verdict": params.get("review_verdict", ""),
        "proposal_id": params.get("proposal_id", ""),
        "parent_gene_ids": [],
    }

    # Append to genome.jsonl (append-only)
    genome_file = boros_root / "genome.jsonl"
    try:
        with open(genome_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(gene, default=str) + "\n")
    except OSError as e:
        return {"status": "error", "message": f"Failed to write genome: {e}"}

    print(f"[civilization] Gene recorded: {gene_id} | {target_skill} | delta={params.get('score_delta')}")

    return {"status": "ok", "gene_id": gene_id, "gene": gene}
