"""
Meta-Learning Model — tracks change-type success rates and optimizes strategy.
Hybrid approach: change-type priors from meta-learning + RL validation from eval.
"""

from __future__ import annotations
import json
from pathlib import Path
import datetime
from typing import Optional


class MetaLearningModel:
    """
    Tracks what types of changes work for what types of capabilities.

    Success rate tracking per change type:
    - additive_code:      Adding new functions
    - semantic_tune:      Editing SKILL.md / prompts
    - refactor_existing:  Rewriting existing code
    - compositional:     Chaining skills together

    Anti-brute-force:
    - Block a file if it regressed 2x in a row
    - Track consecutive failures per file
    """

    CHANGE_TYPES = [
        "additive_code",
        "semantic_tune",
        "refactor_existing",
        "compositional",
    ]

    def __init__(self, boros_root: Path | None = None):
        self.boros_root = boros_root or Path(__file__).parent.parent.parent
        self.meta_file = self.boros_root / "session" / "meta_model.json"
        self.data = self._load()

    def _load(self) -> dict:
        if self.meta_file.exists():
            return json.loads(self.meta_file.read_text())
        return {
            "version": "1.0",
            "change_type_success_rate": {ct: 0.0 for ct in self.CHANGE_TYPES},
            "change_type_attempts": {ct: 0 for ct in self.CHANGE_TYPES},
            "capability_history": {},
            "file_history": {},
            "blocked_change_types": [],
            "last_updated": "",
        }

    def _save(self) -> None:
        self.data["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
        self.meta_file.parent.mkdir(parents=True, exist_ok=True)
        self.meta_file.write_text(json.dumps(self.data, indent=2))

    def record_outcome(
        self,
        change_type: str,
        capability: str,
        target_file: str,
        outcome: str,  # "improved", "regressed", "no_change"
        score_delta: float = 0.0,
    ) -> None:
        """Record the outcome of a change. Updates success rates using EMA."""
        if change_type not in self.CHANGE_TYPES:
            return

        self.data["change_type_attempts"][change_type] += 1

        # Update success rate (EMA: 0.9 old + 0.1 new)
        old_rate = self.data["change_type_success_rate"].get(change_type, 0.0)
        new_outcome = 1.0 if outcome == "improved" else 0.0
        new_rate = 0.9 * old_rate + 0.1 * new_outcome
        self.data["change_type_success_rate"][change_type] = new_rate

        # Update capability history
        if capability not in self.data["capability_history"]:
            self.data["capability_history"][capability] = {
                "last_change_type": None,
                "last_outcome": None,
                "total_improvements": 0,
                "total_regressions": 0,
            }

        cap_hist = self.data["capability_history"][capability]
        cap_hist["last_change_type"] = change_type
        cap_hist["last_outcome"] = outcome
        if outcome == "improved":
            cap_hist["total_improvements"] += 1
        elif outcome == "regressed":
            cap_hist["total_regressions"] += 1

        # Update file history (anti-brute-force)
        if target_file not in self.data["file_history"]:
            self.data["file_history"][target_file] = {
                "consecutive_failures": 0,
                "last_change_type": None,
                "last_outcome": None,
            }

        file_hist = self.data["file_history"][target_file]
        if outcome == "regressed":
            file_hist["consecutive_failures"] += 1
            if file_hist["consecutive_failures"] >= 2:
                if change_type not in self.data["blocked_change_types"]:
                    self.data["blocked_change_types"].append(change_type)
        else:
            file_hist["consecutive_failures"] = 0
            if change_type in self.data["blocked_change_types"]:
                self.data["blocked_change_types"].remove(change_type)

        file_hist["last_change_type"] = change_type
        file_hist["last_outcome"] = outcome

        self._save()

    def suggest_change_type(self, capability: str) -> str:
        """Suggest the best change type for a capability."""
        cap_hist = self.data["capability_history"].get(capability, {})
        last_type = cap_hist.get("last_change_type")
        last_outcome = cap_hist.get("last_outcome")

        if last_outcome == "improved" and last_type:
            return last_type

        if last_outcome == "regressed" and last_type:
            alternatives = [ct for ct in self.CHANGE_TYPES if ct != last_type]
            if alternatives:
                return max(
                    alternatives,
                    key=lambda ct: self.data["change_type_success_rate"].get(ct, 0.0),
                )

        available = [
            ct for ct in self.CHANGE_TYPES
            if ct not in self.data["blocked_change_types"]
        ]
        if not available:
            return "additive_code"

        return max(
            available,
            key=lambda ct: self.data["change_type_success_rate"].get(ct, 0.0),
        )

    def should_block_file(self, target_file: str) -> tuple[bool, str]:
        """Anti-brute-force: block if file regressed 2+ times in a row."""
        file_hist = self.data["file_history"].get(target_file, {})
        failures = file_hist.get("consecutive_failures", 0)

        if failures >= 2:
            return True, f"File regressed {failures} consecutive times."
        return False, ""

    def get_success_rate(self, change_type: str) -> float:
        return self.data["change_type_success_rate"].get(change_type, 0.0)

    def get_all_rates(self) -> dict[str, float]:
        return dict(self.data["change_type_success_rate"])

    def is_blocked(self, change_type: str) -> bool:
        return change_type in self.data.get("blocked_change_types", [])


class RLValidation:
    """
    RL-based validation using the eval engine as the environment.
    Proposals are actions, score improvements are rewards.
    """

    def __init__(self, meta_model: MetaLearningModel):
        self.meta_model = meta_model

    def evaluate_proposal(self, proposal: dict) -> dict:
        """
        Evaluate a change proposal using learned policy.
        Returns: {action, expected_reward, risk, confidence}
        """
        change_type = proposal.get("change_type", "")
        capability = proposal.get("capability", "")
        target_file = proposal.get("target_file", "")

        blocked, reason = self.meta_model.should_block_file(target_file)
        if blocked:
            return {
                "action": "block",
                "reason": reason,
                "expected_reward": 0.0,
                "risk": 1.0,
                "confidence": 0.0,
            }

        success_rate = self.meta_model.get_success_rate(change_type)
        attempts = self.meta_model.data["change_type_attempts"].get(change_type, 0)
        confidence = min(1.0, attempts / 10.0)
        expected_reward = success_rate * confidence
        risk = (1.0 - success_rate) * (1.0 - confidence)

        action = "approve" if expected_reward > 0.2 else "review"

        return {
            "action": action,
            "expected_reward": expected_reward,
            "risk": risk,
            "confidence": confidence,
            "suggested_change_type": self.meta_model.suggest_change_type(capability),
        }

    def update_policy(
        self, proposal: dict, outcome: str, score_delta: float
    ) -> None:
        """Update policy based on outcome."""
        self.meta_model.record_outcome(
            change_type=proposal.get("change_type", ""),
            capability=proposal.get("capability", ""),
            target_file=proposal.get("target_file", ""),
            outcome=outcome,
            score_delta=score_delta,
        )