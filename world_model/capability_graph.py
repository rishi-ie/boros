"""
Capability Graph — World Model v2 for Boros.
A DAG of capabilities with tiers, prerequisites, and emergent properties.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional


class CapabilityNode:
    """A single capability in the world model."""

    def __init__(
        self,
        name: str,
        tier: int,
        description: str = "",
        prerequisites: list[str] | None = None,
        children: list[str] | None = None,
        emergent_from: list[str] | None = None,
        metric: str = "",
        transfer_priority: str = "NORMAL",
    ):
        self.name = name
        self.tier = tier
        self.description = description
        self.prerequisites = prerequisites or []
        self.children = children or []
        self.emergent_from = emergent_from or []
        self.metric = metric
        self.transfer_priority = transfer_priority
        self.current_score = 0.0
        self.high_water_mark = 0.0
        self.evidence: list[dict] = []

    def is_unlocked(self, graph: CapabilityGraph) -> bool:
        """Check if all prerequisites are met for this capability."""
        for prereq in self.prerequisites:
            prereq_node = graph.get(prereq)
            if prereq_node is None:
                continue  # Unknown capability, assume ok
            # Prerequisite must be at least tier - 1 to unlock
            if prereq_node.high_water_mark < (self.tier - 1) / 4:
                return False
        return True

    def can_emergence(self, graph: CapabilityGraph) -> bool:
        """Check if emergent capability can manifest."""
        if not self.emergent_from:
            return False
        for source in self.emergent_from:
            node = graph.get(source)
            if node is None or node.current_score < 0.8:
                return False
        return True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "tier": self.tier,
            "description": self.description,
            "prerequisites": self.prerequisites,
            "children": self.children,
            "emergent_from": self.emergent_from,
            "metric": self.metric,
            "transfer_priority": self.transfer_priority,
            "current_score": self.current_score,
            "high_water_mark": self.high_water_mark,
            "evidence": self.evidence,
        }


class CapabilityGraph:
    """
    World Model v2 — Capability DAG with tier progression,
    prerequisite checking, and emergent capability detection.
    """

    def __init__(self, world_model_path: str | Path | None = None):
        self.nodes: dict[str, CapabilityNode] = {}
        self.terminal_goals: list[str] = []
        if world_model_path:
            self.load(world_model_path)

    def load(self, path: str | Path) -> None:
        """Load world model from JSON."""
        data = json.loads(Path(path).read_text())
        graph_data = data.get("capability_graph", {})

        for name, info in graph_data.items():
            self.nodes[name] = CapabilityNode(
                name=name,
                tier=info.get("tier", 1),
                description=info.get("description", ""),
                prerequisites=info.get("prerequisites", []),
                children=info.get("children", []),
                emergent_from=info.get("emergent_from", []),
                metric=info.get("metric", ""),
                transfer_priority=info.get("transfer_priority", "NORMAL"),
            )

        # Load scores from state
        scores_path = Path(path).parent / "session" / "world_model_scores.json"
        if scores_path.exists():
            scores_data = json.loads(scores_path.read_text())
            for name, score_info in scores_data.items():
                node = self.nodes.get(name)
                if node:
                    node.current_score = score_info.get("current_score", 0.0)
                    node.high_water_mark = score_info.get("high_water_mark", 0.0)
                    node.evidence = score_info.get("evidence", [])

        self.terminal_goals = data.get("dynamic_goals", {}).get("terminal", "")

    def save(self, path: str | Path) -> None:
        """Save world model to JSON (capability graph only — not full world model file)."""
        capability_graph = {}
        for name, node in self.nodes.items():
            capability_graph[name] = {
                "tier": node.tier,
                "description": node.description,
                "prerequisites": node.prerequisites,
                "children": node.children,
                "emergent_from": node.emergent_from,
                "metric": node.metric,
                "transfer_priority": node.transfer_priority,
            }

        data = {
            "version": "2.0",
            "capability_graph": capability_graph,
            "tiers": {
                "tier_0": "Can use with explicit instructions",
                "tier_1": "Can perform independently",
                "tier_2": "Can teach others",
                "tier_3": "Superhuman on benchmarks",
                "tier_4": "Masters any task in domain instantly",
            },
            "dynamic_goals": {
                "terminal": "AGI = all tier_4 capabilities achieved",
                "milestones": [
                    {"name": "Narrow Mastery", "criteria": "One domain at tier_4"},
                    {"name": "Broad Competence", "criteria": "10+ domains at tier_3"},
                    {"name": "AGI Prime", "criteria": "All domains at tier_4"},
                ],
            },
            "self_modification_bounds": {
                "can_change": [
                    "skills",
                    "tests",
                    "config",
                    "metacognition_tuning",
                    "world_model.children",
                    "world_model.prerequisites",
                    "world_model.metrics",
                ],
                "cannot_change": [
                    "world_model.terminal",
                    "world_model.self_modification_bounds",
                    "safety_layer",
                    "version",
                ],
                "configurable_by": "operator_only",
            },
            "dynamic_discovery": {
                "allowed": True,
                "process": "Boros proposes → operator approves → integrated",
            },
        }

        Path(path).write_text(json.dumps(data, indent=2))

    def get(self, name: str) -> Optional[CapabilityNode]:
        return self.nodes.get(name)

    def update_score(self, name: str, score: float, evidence: str = "") -> None:
        """Update a capability's score and evidence."""
        node = self.nodes.get(name)
        if node is None:
            return

        node.current_score = score
        if score > node.high_water_mark:
            node.high_water_mark = score

        if evidence:
            node.evidence.append(
                {
                    "evidence": evidence,
                    "timestamp": self._timestamp(),
                }
            )

        # Persist to scores file
        self._save_scores()

    def _save_scores(self) -> None:
        """Save current scores to persistent storage."""
        scores_path = Path(__file__).parent.parent / "session" / "world_model_scores.json"
        scores_path.parent.mkdir(parents=True, exist_ok=True)
        scores = {}
        for name, node in self.nodes.items():
            scores[name] = {
                "current_score": node.current_score,
                "high_water_mark": node.high_water_mark,
                "evidence": node.evidence,
            }
        scores_path.write_text(json.dumps(scores, indent=2))

    def get_ready_candidates(self) -> list[str]:
        """Get capabilities that are unlocked and ready to improve."""
        candidates = []
        for name, node in self.nodes.items():
            if node.is_unlocked(self) and node.current_score < 0.95:
                candidates.append(name)

        return sorted(
            candidates,
            key=lambda n: (-self.nodes[n].tier, -self.nodes[n].current_score),
        )

    def get_emergent_capabilities(self) -> list[str]:
        """Detect capabilities whose emergent prerequisites are met."""
        return [name for name, node in self.nodes.items() if node.can_emergence(self)]

    def is_agi(self) -> bool:
        """Check if all capabilities have reached AGI tier (4)."""
        return all(node.high_water_mark >= 0.9 for node in self.nodes.values())

    def get_progress_summary(self) -> dict:
        """Get overall progress toward AGI."""
        tiers = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
        for node in self.nodes.values():
            score_tier = min(4, int(node.high_water_mark * 4))
            tiers[score_tier] += 1

        total = len(self.nodes)
        return {
            "total_capabilities": total,
            "tier_distribution": tiers,
            "progress_pct": sum(tiers[i] for i in range(1, 5)) / max(1, total) * 100,
            "is_agi": self.is_agi(),
            "ready_to_improve": len(self.get_ready_candidates()),
            "emergent_ready": len(self.get_emergent_capabilities()),
        }

    def add_capability(self, name: str, node: CapabilityNode) -> None:
        """Add a new capability (operator-approved dynamic discovery)."""
        self.nodes[name] = node
        self._save_scores()

    def _timestamp(self) -> str:
        import datetime
        return datetime.datetime.utcnow().isoformat() + "Z"