"""Tests for the civilization skill."""

import json
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add boros root to path for imports
BOROS_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BOROS_ROOT.parent))


class MockKernel:
    """Minimal kernel mock for testing civilization functions."""
    def __init__(self, boros_root):
        self.boros_root = Path(boros_root)
        self.registry = {}


def setup_test_instance(tmp_dir):
    """Create a minimal Boros instance for testing."""
    tmp = Path(tmp_dir)

    # Create world model
    wm = {
        "version": "2.0",
        "categories": {
            "memory": {
                "name": "Memory",
                "weight": 3.0,
                "related_skills": ["memory"],
                "anchors": ["test"],
                "rubric": {"level_1": "bad", "level_2": "ok"},
                "failure_modes": ["none"],
            }
        }
    }
    (tmp / "world_model.json").write_text(json.dumps(wm, indent=2))

    # Create session dir
    (tmp / "session").mkdir(parents=True, exist_ok=True)
    (tmp / "session" / "loop_state.json").write_text(json.dumps({
        "cycle": 5, "mode": "evolution"
    }))

    # Create high water marks
    hw_dir = tmp / "skills" / "eval-bridge" / "state"
    hw_dir.mkdir(parents=True, exist_ok=True)
    (hw_dir / "high_water_marks.json").write_text(json.dumps({"memory": 0.5}))

    # Create lineage
    (tmp / "lineage.json").write_text(json.dumps({"entries": []}))

    return tmp


def test_genesis_identity():
    """Test that a fresh boot creates a genesis identity."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_test_instance(tmp)
        kernel = MockKernel(root)

        from skills.civilization.functions.civ_get_identity import civ_get_identity

        result = civ_get_identity({}, kernel)

        assert result["status"] == "ok", f"Expected ok, got {result}"
        assert result["birth_type"] == "genesis"
        assert result["generation"] == 0
        assert result["instance_id"].startswith("boros-")
        assert result["origin_id"] == result["instance_id"]
        assert result["parents"] == []
        assert "world_model_hash" in result

        # identity.json should exist
        identity = json.loads((root / "identity.json").read_text())
        assert identity["instance_id"] == result["instance_id"]

        # lineage.json should have boot event
        lineage = json.loads((root / "lineage.json").read_text())
        assert lineage["instance_id"] == result["instance_id"]
        assert any(e["event"] == "boot" for e in lineage["entries"])

        print("✔ test_genesis_identity passed")


def test_identity_idempotent():
    """Test that repeated calls return the same identity."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_test_instance(tmp)
        kernel = MockKernel(root)

        from skills.civilization.functions.civ_get_identity import civ_get_identity

        result1 = civ_get_identity({}, kernel)
        result2 = civ_get_identity({}, kernel)

        assert result1["instance_id"] == result2["instance_id"]
        print("✔ test_identity_idempotent passed")


def test_record_gene():
    """Test gene recording."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_test_instance(tmp)
        kernel = MockKernel(root)

        from skills.civilization.functions.civ_get_identity import civ_get_identity
        from skills.civilization.functions.civ_record_gene import civ_record_gene

        # Create identity first
        civ_get_identity({}, kernel)

        result = civ_record_gene({
            "cycle": 5,
            "target_skill": "memory",
            "target_file": "skills/memory/functions/memory_page_in.py",
            "approach": "Improved retrieval logic",
            "diff": "--- a/old\n+++ b/new\n@@ -1 +1 @@\n-old\n+new",
            "score_delta": 0.084,
            "score_before": {"memory": 0.625},
            "score_after": {"memory": 0.709},
            "proposal_id": "prop-test1234",
            "review_verdict": "apply",
        }, kernel)

        assert result["status"] == "ok"
        assert result["gene_id"].startswith("gene-")
        assert result["gene"]["origin"] == "evolved"

        # genome.jsonl should exist and have one entry
        genome = (root / "genome.jsonl").read_text().strip().split("\n")
        assert len(genome) == 1
        gene = json.loads(genome[0])
        assert gene["target_skill"] == "memory"
        assert gene["score_delta"] == 0.084

        print("✔ test_record_gene passed")


def test_read_genome():
    """Test genome reading with filters."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_test_instance(tmp)
        kernel = MockKernel(root)

        from skills.civilization.functions.civ_get_identity import civ_get_identity
        from skills.civilization.functions.civ_record_gene import civ_record_gene
        from skills.civilization.functions.civ_read_genome import civ_read_genome

        civ_get_identity({}, kernel)

        # Record two genes
        civ_record_gene({"cycle": 1, "target_skill": "memory", "score_delta": 0.05}, kernel)
        civ_record_gene({"cycle": 2, "target_skill": "reasoning", "score_delta": 0.03}, kernel)

        # Read all
        result = civ_read_genome({}, kernel)
        assert result["total"] == 2
        assert result["stats"]["evolved"] == 2

        # Filter by category
        result = civ_read_genome({"filter_category": "memory"}, kernel)
        assert len(result["genes"]) == 1

        # Limit
        result = civ_read_genome({"limit": 1}, kernel)
        assert len(result["genes"]) == 1

        print("✔ test_read_genome passed")


def test_fork_child():
    """Test fork child preparation."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_test_instance(tmp)
        kernel = MockKernel(root)

        from skills.civilization.functions.civ_get_identity import civ_get_identity
        from skills.civilization.functions.civ_record_gene import civ_record_gene
        from skills.civilization.functions.civ_fork_child import civ_fork_child

        parent_identity = civ_get_identity({}, kernel)
        civ_record_gene({"cycle": 1, "target_skill": "memory", "score_delta": 0.1}, kernel)

        result = civ_fork_child({}, kernel)

        assert result["status"] == "ok"
        assert result["child_id"].startswith("boros-")
        assert result["child_generation"] == 1
        assert result["parent_id"] == parent_identity["instance_id"]

        # identity_seed.json should exist
        assert (root / "identity_seed.json").exists()
        seed = json.loads((root / "identity_seed.json").read_text())
        assert seed["birth_type"] == "fork"
        assert seed["generation"] == 1

        # genome_inherited.jsonl should exist
        assert (root / "genome_inherited.jsonl").exists()
        inherited = (root / "genome_inherited.jsonl").read_text().strip().split("\n")
        assert len(inherited) == 1
        gene = json.loads(inherited[0])
        assert gene["origin"] == "inherited"

        # Lineage should have fork_child event
        lineage = json.loads((root / "lineage.json").read_text())
        assert any(e["event"] == "fork_child" for e in lineage["entries"])

        print("✔ test_fork_child passed")


def test_child_resolves_identity_from_seed():
    """Test that a child instance resolves identity from seed."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_test_instance(tmp)
        kernel = MockKernel(root)

        from skills.civilization.functions.civ_get_identity import civ_get_identity
        from skills.civilization.functions.civ_fork_child import civ_fork_child

        parent_identity = civ_get_identity({}, kernel)
        fork_result = civ_fork_child({}, kernel)

        # Simulate child: remove parent's identity.json, keep the seed
        (root / "identity.json").unlink()

        # Child boots and resolves identity from seed
        child_identity = civ_get_identity({}, kernel)

        assert child_identity["status"] == "ok"
        assert child_identity["birth_type"] == "fork"
        assert child_identity["generation"] == 1
        assert child_identity["instance_id"] != parent_identity["instance_id"]
        assert len(child_identity["parents"]) == 1
        assert child_identity["parents"][0]["instance_id"] == parent_identity["instance_id"]

        # Seed should be deleted
        assert not (root / "identity_seed.json").exists()

        print("✔ test_child_resolves_identity_from_seed passed")


def test_heartbeat():
    """Test heartbeat writing."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_test_instance(tmp)
        kernel = MockKernel(root)

        from skills.civilization.functions.civ_get_identity import civ_get_identity
        from skills.civilization.functions.civ_heartbeat import civ_heartbeat

        civ_get_identity({}, kernel)

        result = civ_heartbeat({
            "cycle": 10,
            "scores": {"memory": 0.7},
            "last_outcome": "improved",
            "last_delta": 0.05,
            "last_category": "memory",
        }, kernel)

        assert result["status"] == "ok"
        assert (root / "heartbeat.json").exists()

        hb = json.loads((root / "heartbeat.json").read_text())
        assert hb["cycle"] == 10
        assert hb["scores"]["memory"] == 0.7
        assert hb["instance_id"].startswith("boros-")

        print("✔ test_heartbeat passed")


def test_lineage_read():
    """Test lineage reading."""
    with tempfile.TemporaryDirectory() as tmp:
        root = setup_test_instance(tmp)
        kernel = MockKernel(root)

        from skills.civilization.functions.civ_get_identity import civ_get_identity
        from skills.civilization.functions.civ_lineage import civ_lineage_read

        civ_get_identity({}, kernel)

        result = civ_lineage_read({}, kernel)

        assert result["status"] == "ok"
        assert result["identity"]["instance_id"].startswith("boros-")
        assert result["identity"]["birth_type"] == "genesis"
        assert any(e["event"] == "boot" for e in result["events"])

        print("✔ test_lineage_read passed")


if __name__ == "__main__":
    test_genesis_identity()
    test_identity_idempotent()
    test_record_gene()
    test_read_genome()
    test_fork_child()
    test_child_resolves_identity_from_seed()
    test_heartbeat()
    test_lineage_read()
    print("\n🎉 All civilization tests passed!")
