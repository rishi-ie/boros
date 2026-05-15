"""
Reflector Agent — analyzes scores, identifies capability gaps, forms hypotheses.
Reads eval scores, finds low-scoring capabilities, proposes what to improve.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from agents.messages import AgentMessage, MessageType, make_hypothesis, make_status
from agents.bus import get_bus


class ReflectorAgent:
    """
    Reflects on current performance and forms hypotheses.
    Inputs: eval scores, cycle history, capability graph
    Outputs: hypotheses about what to improve next
    """

    def __init__(self, kernel):
        self.kernel = kernel
        self.boros_root = kernel.boros_root
        self.bus = get_bus()
        self._hypothesis_history: list[AgentMessage] = []

        self.bus.subscribe(MessageType.STATUS_REPORT, self._on_status)

    def analyze(self) -> list[AgentMessage]:
        """
        Main analysis: read scores, find gaps, form hypotheses.
        Returns list of hypothesis messages sorted by confidence.
        """
        scores = self._read_scores()
        hypotheses = []

        # Find lowest-scoring capabilities
        for capability, score in sorted(scores.items(), key=lambda x: x[1]):
            if score < 0.7:  # Below threshold
                hypothesis = self._form_hypothesis(capability, score, scores)
                hypotheses.append(hypothesis)
                self._hypothesis_history.append(hypothesis)

        return sorted(hypotheses, key=lambda h: -h.payload.get("confidence", 0))

    def _read_scores(self) -> dict:
        """Read latest eval scores from high_water_marks."""
        hw_file = (
            self.boros_root / "skills" / "eval-bridge" / "state" / "high_water_marks.json"
        )
        if not hw_file.exists():
            return {}
        try:
            return json.loads(hw_file.read_text())
        except Exception:
            return {}

    def _form_hypothesis(
        self, capability: str, score: float, all_scores: dict
    ) -> AgentMessage:
        """Form a hypothesis about improving a capability."""
        change_type = self._suggest_change_type(capability, score, all_scores)

        evidence = f"'{capability}' scored {score:.3f} — below threshold"
        confidence = min(0.9, 1.0 - score)  # Lower score = higher confidence

        return make_hypothesis(
            capability_gap=capability,
            evidence=evidence,
            suggested_change_type=change_type,
            confidence=confidence,
        )

    def _suggest_change_type(
        self, capability: str, score: float, all_scores: dict
    ) -> str:
        """Suggest best change type based on history and score pattern."""
        # Check meta_model for historical data
        meta_file = self.boros_root / "session" / "meta_model.json"
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text())
                cap_hist = meta.get("capability_history", {}).get(capability, {})
                last_type = cap_hist.get("last_change_type")
                last_outcome = cap_hist.get("last_outcome")

                if last_outcome == "improved" and last_type:
                    return last_type
                if last_outcome == "regressed" and last_type:
                    alternatives = [
                        "additive_code", "semantic_tune", "refactor_existing",
                        "compositional"
                    ]
                    alternatives = [t for t in alternatives if t != last_type]
                    if alternatives:
                        return max(
                            alternatives,
                            key=lambda t: meta.get("change_type_success_rate", {}).get(t, 0),
                        )
            except Exception:
                pass

        # Score-based fallback
        if score < 0.3:
            return "additive_code"
        elif score < 0.6:
            return "semantic_tune"
        else:
            return "compositional"

    def _is_stalled(self, capability: str) -> bool:
        """Check if improvement has stalled for this capability."""
        state_file = self.boros_root / "session" / "loop_state.json"
        if not state_file.exists():
            return False
        try:
            state = json.loads(state_file.read_text())
            recent = state.get("recent_improvements", [])
            if len(recent) < 3:
                return False
            recent_scores = [r.get(capability, 0) for r in recent]
            return max(recent_scores) - min(recent_scores) < 0.01
        except Exception:
            return False

    def _on_status(self, msg: AgentMessage) -> None:
        """React to status updates from Reviewer."""
        if msg.sender == "reviewer":
            for hypothesis in self._hypothesis_history:
                if hypothesis.correlation_id == msg.payload.get("proposal_id"):
                    outcome = msg.payload.get("outcome", "unknown")
                    delta = 0.1 if outcome == "improved" else -0.15
                    current = hypothesis.payload.get("confidence", 0.5)
                    hypothesis.payload["confidence"] = max(
                        0.0, min(1.0, current + delta)
                    )

    def get_best_hypothesis(self) -> AgentMessage | None:
        """Get the highest-confidence unacted-upon hypothesis."""
        unacted = [h for h in self._hypothesis_history if not h.payload.get("acted_upon")]
        if not unacted:
            return None
        return max(unacted, key=lambda h: h.payload.get("confidence", 0))

    def mark_acted(self, hypothesis_id: str) -> None:
        """Mark a hypothesis as acted upon."""
        for h in self._hypothesis_history:
            if h.id == hypothesis_id:
                h.payload["acted_upon"] = True

    def get_summary(self) -> dict:
        """Get reflector summary."""
        return {
            "total_hypotheses": len(self._hypothesis_history),
            "unacted": len([h for h in self._hypothesis_history if not h.payload.get("acted_upon")]),
            "best_confidence": max(
                (h.payload.get("confidence", 0) for h in self._hypothesis_history), default=0
            ),
        }