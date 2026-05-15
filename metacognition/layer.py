"""
Metacognition Layer — self-monitoring, confidence calibration, loop detection.
The self-aware layer that watches Boros thinking about Boros.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Optional
import datetime


class MetacognitionLayer:
    """
    Self-monitoring layer for Boros.

    Responsibilities:
    1. Monitor reasoning traces for anomalies
    2. Calibrate confidence (know what you know)
    3. Detect reasoning loops
    4. Detect capability stagnation
    5. Self-modification within safety bounds
    """

    IMMOVABLE = {
        "world_model.terminal",
        "world_model.self_modification_bounds",
        "safety_layer",
        "metacognition.immovable",
    }

    def __init__(self, boros_root: Path | None = None):
        self.boros_root = boros_root or Path(__file__).parent.parent.parent
        self.state_file = self.boros_root / "session" / "metacognition.json"
        self.state = self._load()
        self._reasoning_history: list[str] = []
        self._last_reasoning: list[str] = []

    def _load(self) -> dict:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return {
            "coherence_history": [],
            "confidence_calibration": {},
            "loop_count": 0,
            "anomalies_detected": 0,
            "self_modifications": [],
        }

    def _save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2))

    def monitor_reasoning(self, reasoning_trace: list[str]) -> dict:
        """
        Monitor a reasoning trace for anomalies.
        Returns: {coherence, anomalies, loop, needs_attention}
        """
        anomalies = []

        coherence = self._check_coherence(reasoning_trace)

        if self._has_contradiction(reasoning_trace):
            anomalies.append("CONTRADICTION: reasoning steps contradict each other")
            self.state["anomalies_detected"] += 1

        if self._has_unfounded_claim(reasoning_trace):
            anomalies.append("UNFOUNDED_CLAIM: assertion without supporting evidence")

        if self._is_repeating_conclusions(reasoning_trace):
            anomalies.append("REPEATING_CONCLUSIONS")

        loop_detected = self._detect_loop(reasoning_trace)
        if loop_detected:
            self.state["loop_count"] += 1
            anomalies.append(f"LOOP_DETECTED (count: {self.state['loop_count']})")

        self._reasoning_history = reasoning_trace[-20:]
        self.state["coherence_history"].append(coherence)
        if len(self.state["coherence_history"]) > 100:
            self.state["coherence_history"] = self.state["coherence_history"][-100:]

        self._save()

        return {
            "coherence": coherence,
            "anomalies": anomalies,
            "loop": loop_detected,
            "needs_attention": len(anomalies) > 0 or coherence < 0.5,
        }

    def _check_coherence(self, trace: list[str]) -> float:
        """Check if reasoning steps form a coherent chain."""
        if len(trace) < 2:
            return 1.0
        shared = sum(
            1
            for i in range(len(trace) - 1)
            if len(set(trace[i].lower().split()) & set(trace[i + 1].lower().split())) >= 2
        )
        return shared / max(1, len(trace) - 1)

    def _has_contradiction(self, trace: list[str]) -> bool:
        positive = ["always", "definitely", "certainly", "proven", "confirmed"]
        negative = ["never", "impossible", "cannot"]
        pos = sum(1 for s in trace for w in positive if w in s.lower())
        neg = sum(1 for s in trace for w in negative if w in s.lower())
        return pos > 0 and neg > 0

    def _has_unfounded_claim(self, trace: list[str]) -> bool:
        claims = ["should", "must", "will definitely", "obviously"]
        evidence = ["because", "evidence", "data", "shows", "tested", "proven"]
        for step in trace:
            has_claim = any(c in step.lower() for c in claims)
            has_ev = any(e in step.lower() for e in evidence)
            if has_claim and not has_ev and len(step) < 100:
                return True
        return False

    def _is_repeating_conclusions(self, trace: list[str]) -> bool:
        conclusions = [s.strip()[-50:] for s in trace[-5:]]
        return len(set(conclusions)) < len(conclusions) * 0.5

    def _detect_loop(self, trace: list[str]) -> bool:
        if len(trace) < 6:
            return False
        sigs = [s[:30].lower().strip() for s in trace[-6:]]
        if len(self._last_reasoning) >= 6:
            prev = [s[:30].lower().strip() for s in self._last_reasoning[-6:]]
            if sigs == prev:
                return True
        self._last_reasoning = trace[-10:]
        return False

    def calibrate_confidence(
        self, prediction: str, actual_outcome: Any
    ) -> dict:
        """Calibrate confidence: compare predicted vs actual."""
        pred_conf = (
            self.state["confidence_calibration"].get(prediction, {}).get(
                "predicted_confidence", 0.5
            )
        )
        actual = 1.0 if actual_outcome else 0.0
        error = abs(pred_conf - actual)

        prev_entry = self.state["confidence_calibration"].get(prediction, {})
        prev_error = prev_entry.get("calibration_error", 0.5)
        new_error = 0.9 * prev_error + 0.1 * error

        self.state["confidence_calibration"][prediction] = {
            "predicted_confidence": pred_conf,
            "actual_outcome": actual,
            "calibration_error": new_error,
            "count": prev_entry.get("count", 0) + 1,
        }
        self._save()

        return {
            "calibrated": new_error < 0.1,
            "calibration_error": new_error,
            "needs_retraining": new_error > 0.2,
        }

    def detect_stagnation(self, capability: str, history: list[float]) -> dict:
        """Detect if improvement has stalled."""
        if len(history) < 5:
            return {"stalled": False}
        recent = history[-5:]
        if max(recent) - min(recent) < 0.01:
            return {
                "stalled": True,
                "since": len(history) - 5,
                "suggestion": f"'{capability}' stalled. Try a different change type.",
            }
        return {"stalled": False}

    def suggest_intervention(self) -> Optional[str]:
        """Suggest metacognitive intervention."""
        if self.state["loop_count"] >= 3:
            self.state["loop_count"] = 0
            self._save()
            return "LOOP_BREAK: Reset approach. Try a completely different strategy."

        recent = self.state["coherence_history"][-10:]
        if recent and sum(recent) / len(recent) < 0.4:
            return "COHERENCE_LOW: Review reasoning chain. Ensure each step follows."

        if self.state["anomalies_detected"] >= 5:
            self.state["anomalies_detected"] = 0
            self._save()
            return "ANOMALY_SUMMARY: Multiple anomalies. Pause and verify assumptions."

        return None

    def self_modify(self, component: str, modification: dict) -> dict:
        """Attempt self-modification within safety bounds."""
        if component in self.IMMOVABLE:
            return {
                "allowed": False,
                "reason": f"'{component}' is immovable. Operator approval required.",
            }
        self.state["self_modifications"].append({
            "component": component,
            "modification": modification,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        })
        self._save()
        return {"allowed": True, "reason": "Modification allowed within safety bounds."}

    def get_stats(self) -> dict:
        """Get metacognition statistics."""
        return {
            "loop_count": self.state["loop_count"],
            "anomalies_detected": self.state["anomalies_detected"],
            "self_modifications": len(self.state["self_modifications"]),
            "avg_coherence": (
                sum(self.state["coherence_history"]) /
                max(1, len(self.state["coherence_history"]))
            ),
        }