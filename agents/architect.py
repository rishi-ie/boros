"""
Architect Agent — designs and implements code changes.
Takes hypotheses from Reflector, creates change proposals for Reviewer.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from agents.messages import AgentMessage, MessageType, make_proposal, make_status
from agents.bus import get_bus


class ArchitectAgent:
    """
    Designs and implements changes.
    Inputs: hypotheses from Reflector
    Outputs: change proposals to Reviewer
    """

    CAPABILITY_MAP = {
        "memory": "skills/memory/SKILL.md",
        "reasoning": "skills/reasoning/SKILL.md",
        "tool_use": "skills/tool-use/SKILL.md",
        "evolution": "skills/meta-evolution/SKILL.md",
        "meta_eval": "skills/meta-evaluation/SKILL.md",
        "reflection": "skills/reflection/SKILL.md",
        "planning": "skills/planning/SKILL.md",
        "composition": "skills/skill-forge/SKILL.md",
        "communication": "skills/communication/SKILL.md",
    }

    DEFAULT_TARGET = "skills/meta-evolution/SKILL.md"

    def __init__(self, kernel):
        self.kernel = kernel
        self.boros_root = kernel.boros_root
        self.bus = get_bus()
        self._proposals: list[AgentMessage] = []
        self._revision_counter = 0

        self.bus.subscribe(MessageType.HYPOTHESIS, self._on_hypothesis)
        self.bus.subscribe(MessageType.REVISION_REQUEST, self._on_revision)

    def design_proposal(self, hypothesis: AgentMessage) -> AgentMessage:
        """
        Design a change proposal based on a hypothesis.
        Returns a PROPOSAL message for the Reviewer.
        """
        change_type = hypothesis.payload["suggested_change_type"]
        capability = hypothesis.payload["capability_gap"]

        target_file, code_change = self._design_change(change_type, capability)
        rollback_plan = self._design_rollback(target_file)

        proposal = make_proposal(
            change_type=change_type,
            target_file=target_file,
            code_change=code_change,
            rationale=f"Improve '{capability}' based on hypothesis "
                     f"(confidence={hypothesis.payload['confidence']:.2f})",
            expected_score_impact=self._estimate_impact(change_type, capability),
            rollback_plan=rollback_plan,
        )

        proposal.correlation_id = hypothesis.id
        self._proposals.append(proposal)
        return proposal

    def _design_change(self, change_type: str, capability: str) -> tuple[str, str]:
        """Design the actual code change."""
        target = self.CAPABILITY_MAP.get(capability, self.DEFAULT_TARGET)

        designs = {
            "additive_code": lambda: self._design_additive(capability),
            "semantic_tune": lambda: self._design_semantic_tune(capability),
            "refactor_existing": lambda: self._design_refactor(capability),
            "compositional": lambda: self._design_composition(capability),
        }

        design_func = designs.get(change_type, designs["semantic_tune"])
        return target, design_func()

    def _design_additive(self, capability: str) -> str:
        return f'''

# NEW FUNCTION for {capability}
def improve_{capability.replace("-", "_")}(context):
    """
    Improves {capability} by analyzing patterns and applying best practices.
    """
    patterns = analyze_patterns(context)
    return apply_best_practices(patterns)
'''

    def _design_semantic_tune(self, capability: str) -> str:
        return f'''
## {capability.upper()} IMPROVEMENT

Updated to prioritize {capability} enhancement:
1. Pattern recognition in {capability} tasks
2. Best practice extraction from successful cycles
3. Proactive capability building
4. Metric tracking and feedback
'''

    def _design_refactor(self, capability: str) -> str:
        return f'''
# REFACTOR: {capability}
Replaced ad-hoc implementation with structured approach:
- Cleaner separation of concerns
- Better error handling
- Improved metric tracking
- Clearer documentation
'''

    def _design_composition(self, capability: str) -> str:
        return f'''
# COMPOSITION: {capability}
sequence:
  - skill: memory_retrieve
    params: {{query: "{capability}_patterns"}}
  - skill: reasoning_decompose
    params: {{problem: "improve_{capability}"}}
  - skill: tool_execute
  - skill: memory_store
    params: {{insights: "from_above"}}
'''

    def _design_rollback(self, target_file: str) -> str:
        return f"Restore {target_file} from previous snapshot via version_control.rollback()"

    def _estimate_impact(self, change_type: str, capability: str) -> float:
        """Estimate expected score impact."""
        meta_file = self.boros_root / "session" / "meta_model.json"
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text())
                rate = meta.get("change_type_success_rate", {}).get(change_type, 0.3)
                return rate * 0.2
            except Exception:
                pass

        estimates = {
            "additive_code": 0.15,
            "semantic_tune": 0.10,
            "refactor_existing": 0.08,
            "compositional": 0.12,
        }
        return estimates.get(change_type, 0.05)

    def _on_hypothesis(self, msg: AgentMessage) -> None:
        """React to new hypothesis from Reflector."""
        proposal = self.design_proposal(msg)
        self.bus.publish(proposal)

    def _on_revision(self, msg: AgentMessage) -> None:
        """React to revision request from Reviewer."""
        issues = msg.payload["issues"]
        self._revision_counter += 1

        original_id = msg.payload.get("proposal_id")
        for proposal in self._proposals:
            if proposal.id == original_id:
                revised = self._incorporate_revision(proposal, issues)
                self.bus.publish(revised)
                break

    def _incorporate_revision(
        self, proposal: AgentMessage, issues: list[str]
    ) -> AgentMessage:
        """Incorporate reviewer feedback into proposal."""
        revision_note = (
            f"\n# REVISION {self._revision_counter}: "
            f"Addressed issues: {', '.join(issues)}"
        )

        revised = make_proposal(
            change_type=proposal.payload["change_type"],
            target_file=proposal.payload["target_file"],
            code_change=proposal.payload["code_change"] + revision_note,
            rationale=proposal.payload["rationale"] + " [REVISED]",
            expected_score_impact=proposal.payload["expected_score_impact"],
            rollback_plan=proposal.payload["rollback_plan"],
        )
        revised.correlation_id = proposal.correlation_id
        return revised

    def get_proposal(self, proposal_id: str) -> AgentMessage | None:
        """Get a proposal by ID."""
        for p in self._proposals:
            if p.id == proposal_id:
                return p
        return None

    def get_summary(self) -> dict:
        """Get architect summary."""
        return {
            "total_proposals": len(self._proposals),
            "revision_count": self._revision_counter,
        }