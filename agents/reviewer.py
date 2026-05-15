"""
Reviewer Agent — meta-evaluates proposals, safety checks, quality gate.
All proposals must pass through Reviewer before execution.
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Optional
from agents.messages import AgentMessage, MessageType, make_approval, make_rejection, make_revision
from agents.bus import get_bus


class ReviewerAgent:
    """
    Meta-evaluation and safety gate.
    Inputs: proposals from Architect
    Outputs: approval/rejection/revision to Orchestrator
    """

    IMMUTABLES = [
        "world_model.json",
        "kernel.py",
        "safety",
        "self_modification_bounds",
        "version_control",
    ]

    def __init__(self, kernel):
        self.kernel = kernel
        self.boros_root = kernel.boros_root
        self.bus = get_bus()
        self._rejection_history: list[str] = []

        self.bus.subscribe(MessageType.PROPOSAL, self._on_proposal)

    def evaluate(self, proposal: AgentMessage) -> AgentMessage:
        """
        Evaluate a proposal against safety, quality, and regression criteria.
        Returns APPROVAL, REJECTION, or REVISION_REQUEST.
        """
        payload = proposal.payload

        # Safety: immutable components
        safety = self._check_safety(payload)
        if not safety["safe"]:
            self._record_rejection(payload["change_type"])
            return make_rejection(
                proposal_id=proposal.id,
                reason=f"Safety violation: {safety['reason']}",
                blocked_types=[payload.get("change_type")],
            )

        # Quality: not cosmetic-only
        quality = self._check_quality(payload)
        if not quality["pass"]:
            return make_revision(
                proposal_id=proposal.id,
                issues=quality["issues"],
                suggestions=quality["suggestions"],
            )

        # Regression: anti-brute-force
        regression = self._check_regression(payload)
        if regression["blocked"]:
            self._record_rejection(payload["change_type"])
            return make_rejection(
                proposal_id=proposal.id,
                reason=f"Regression blocked: {regression['reason']}",
                blocked_types=[payload.get("change_type")],
            )

        # Impact: must have meaningful expected impact
        if payload.get("expected_score_impact", 0) < 0.01:
            return make_revision(
                proposal_id=proposal.id,
                issues=["Expected impact too low (< 0.01)"],
                suggestions=["Increase scope or choose higher-impact capability"],
            )

        # All checks passed
        return make_approval(
            proposal_id=proposal.id,
            conditions=["Monitor for regressions in next 3 cycles"],
        )

    def _check_safety(self, payload: dict) -> dict:
        """Check if proposal modifies immutable components."""
        target_file = payload.get("target_file", "")

        for immutable in self.IMMUTABLES:
            if immutable in target_file:
                return {"safe": False, "reason": f"Immutable: {immutable}"}

        change_type = payload.get("change_type", "")
        blocked = self._get_blocked_changes()
        if change_type in blocked:
            return {"safe": False, "reason": f"Change type blocked: {change_type}"}

        return {"safe": True}

    def _check_quality(self, payload: dict) -> dict:
        """Check if proposal is substantive, not cosmetic."""
        code_change = payload.get("code_change", "")
        change_type = payload.get("change_type", "")

        issues = []
        suggestions = []

        if self._is_cosmetic_only(code_change):
            issues.append("Proposal is cosmetic-only (no substantive logic)")
            suggestions.append("Include actual logic changes")

        if len(code_change.strip()) < 50 and change_type != "semantic_tune":
            issues.append("Change too small to have meaningful impact")
            suggestions.append("Increase scope or combine with related changes")

        if not payload.get("rationale"):
            issues.append("Missing rationale")
            suggestions.append("Explain why this should improve the capability")

        if not payload.get("rollback_plan"):
            issues.append("Missing rollback plan")
            suggestions.append("Define how to restore previous state if needed")

        return {"pass": len(issues) == 0, "issues": issues, "suggestions": suggestions}

    def _check_regression(self, payload: dict) -> dict:
        """Anti-brute-force: block if file regressed recently."""
        target_file = payload.get("target_file", "")
        meta_file = self.boros_root / "session" / "meta_model.json"

        if not meta_file.exists():
            return {"blocked": False}

        try:
            meta = json.loads(meta_file.read_text())
            file_hist = meta.get("file_history", {}).get(target_file, {})
            failures = file_hist.get("consecutive_failures", 0)

            if failures >= 2:
                return {
                    "blocked": True,
                    "reason": f"'{target_file}' regressed {failures} times. "
                             "Take a different approach before retrying.",
                }
        except Exception:
            pass

        return {"blocked": False}

    def _get_blocked_changes(self) -> list[str]:
        """Get currently blocked change types."""
        meta_file = self.boros_root / "session" / "meta_model.json"
        if not meta_file.exists():
            return []
        try:
            meta = json.loads(meta_file.read_text())
            return meta.get("blocked_change_types", [])
        except Exception:
            return []

    def _record_rejection(self, change_type: str) -> None:
        """Record rejection for anti-brute-force."""
        self._rejection_history.append(change_type)

    def _is_cosmetic_only(self, code_change: str) -> bool:
        """Check if code change is cosmetic (no logic change)."""
        lines = [l.strip() for l in code_change.split("\n") if l.strip()]
        if not lines:
            return True

        patterns = [
            r"^def\s+",
            r"^class\s+",
            r"^if\s+",
            r"^for\s+",
            r"^return\s+",
            r"^#",
            r"\w+\s*=\s*",
        ]

        for line in lines:
            for pattern in patterns:
                if re.match(pattern, line):
                    return False

        return True

    def _on_proposal(self, msg: AgentMessage) -> None:
        """Handle incoming proposal."""
        result = self.evaluate(msg)
        result.correlation_id = msg.correlation_id
        self.bus.publish(result)

    def get_summary(self) -> dict:
        """Get reviewer summary."""
        return {
            "total_rejections": len(self._rejection_history),
            "blocked_types": list(set(self._rejection_history[-10:])),
        }