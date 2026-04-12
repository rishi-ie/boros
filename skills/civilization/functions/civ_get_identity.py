"""civ_get_identity — Read or generate this instance's identity."""

import json
import datetime
from pathlib import Path
from ._internal.identity_utils import generate_instance_id, compute_world_model_hash


def civ_get_identity(params: dict, kernel=None) -> dict:
    """Read or generate this instance's identity.

    On first call with no identity:
      - If identity_seed.json exists → this is a child being born (fork or breed).
        Resolves seed into a full identity, deletes seed.
      - If no seed exists → genesis. Creates root identity.
    On subsequent calls:
      - Returns existing identity from identity.json.

    Returns:
        The identity dict with instance_id, origin_id, parents, birth_type,
        generation, born_at, world_model_hash.
    """
    boros_root = Path(kernel.boros_root) if kernel else Path(".")

    identity_file = boros_root / "identity.json"
    seed_file = boros_root / "identity_seed.json"

    # Fast path: identity already exists
    if identity_file.exists():
        try:
            identity = json.loads(identity_file.read_text(encoding="utf-8"))
            return {"status": "ok", **identity}
        except (json.JSONDecodeError, OSError) as e:
            return {"status": "error", "message": f"Failed to read identity.json: {e}"}

    # Path 2: identity_seed.json exists — this is a child being born
    if seed_file.exists():
        try:
            seed = json.loads(seed_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            return {"status": "error", "message": f"Failed to read identity_seed.json: {e}"}

        identity = {
            "instance_id": generate_instance_id(),
            "origin_id": seed.get("origin_id", seed.get("parent_instance_id", "")),
            "parents": seed.get("parents", []),
            "birth_type": seed.get("birth_type", "fork"),
            "generation": seed.get("generation", 1),
            "born_at": datetime.datetime.utcnow().isoformat() + "Z",
            "world_model_hash": compute_world_model_hash(boros_root),
        }

        # Write permanent identity
        identity_file.write_text(json.dumps(identity, indent=2), encoding="utf-8")

        # Delete the seed — it's consumed
        try:
            seed_file.unlink()
        except OSError:
            pass

        # Update lineage.json with identity info
        _update_lineage_with_identity(boros_root, identity)

        print(f"[civilization] Identity resolved from seed: {identity['instance_id']} "
              f"(birth_type={identity['birth_type']}, generation={identity['generation']})")

        return {"status": "ok", **identity}

    # Path 3: Genesis — first-ever boot of this instance
    identity = {
        "instance_id": generate_instance_id(),
        "origin_id": "",  # filled below
        "parents": [],
        "birth_type": "genesis",
        "generation": 0,
        "born_at": datetime.datetime.utcnow().isoformat() + "Z",
        "world_model_hash": compute_world_model_hash(boros_root),
    }
    identity["origin_id"] = identity["instance_id"]  # root of its own lineage

    # Write permanent identity
    identity_file.write_text(json.dumps(identity, indent=2), encoding="utf-8")

    # Initialize lineage.json with identity info
    _update_lineage_with_identity(boros_root, identity)

    print(f"[civilization] Genesis identity created: {identity['instance_id']}")

    return {"status": "ok", **identity}


def _update_lineage_with_identity(boros_root: Path, identity: dict):
    """Update lineage.json with identity-level fields.

    Preserves any existing entries array from the old format.
    """
    lineage_file = boros_root / "lineage.json"
    lineage = {"entries": []}

    if lineage_file.exists():
        try:
            lineage = json.loads(lineage_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            lineage = {"entries": []}

    # Ensure entries key exists
    if "entries" not in lineage:
        lineage["entries"] = []

    # Add identity-level fields at the top
    lineage["instance_id"] = identity["instance_id"]
    lineage["origin_id"] = identity["origin_id"]
    lineage["birth_type"] = identity["birth_type"]
    lineage["generation"] = identity["generation"]
    lineage["born_at"] = identity["born_at"]
    lineage["world_model_hash"] = identity["world_model_hash"]
    lineage["parents"] = identity["parents"]

    # Add boot event
    lineage["entries"].append({
        "event": "boot",
        "timestamp": identity["born_at"],
        "cycle": 0,
        "birth_type": identity["birth_type"],
    })

    lineage_file.write_text(json.dumps(lineage, indent=2), encoding="utf-8")
