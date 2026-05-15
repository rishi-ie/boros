"""
Agent Messages — typed communication between agents.
All agents communicate via these message types.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import datetime
import uuid


class MessageType(Enum):
    HYPOTHESIS = "hypothesis"
    PROPOSAL = "proposal"
    REVISION_REQUEST = "revision"
    APPROVAL = "approval"
    REJECTION = "rejection"
    EXECUTION_RESULT = "result"
    STATUS_REPORT = "status"
    ESCALATION = "escalation"


@dataclass
class AgentMessage:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: MessageType = MessageType.STATUS_REPORT
    sender: str = ""
    recipient: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )
    reply_to: Optional[str] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "reply_to": self.reply_to,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentMessage:
        return cls(
            id=data["id"],
            type=MessageType(data["type"]),
            sender=data.get("sender", ""),
            recipient=data.get("recipient", ""),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", ""),
            reply_to=data.get("reply_to"),
            correlation_id=data.get("correlation_id"),
        )


# ── Factory Functions ──────────────────────────────────────────────────────────

def make_hypothesis(
    capability_gap: str,
    evidence: str,
    suggested_change_type: str,
    confidence: float,
) -> AgentMessage:
    """Reflector → Orchestrator: new hypothesis about what to improve."""
    return AgentMessage(
        type=MessageType.HYPOTHESIS,
        sender="reflector",
        recipient="orchestrator",
        payload={
            "capability_gap": capability_gap,
            "evidence": evidence,
            "suggested_change_type": suggested_change_type,
            "confidence": confidence,
        },
    )


def make_proposal(
    change_type: str,
    target_file: str,
    code_change: str,
    rationale: str,
    expected_score_impact: float,
    rollback_plan: str,
) -> AgentMessage:
    """Architect → Reviewer: specific change proposal."""
    return AgentMessage(
        type=MessageType.PROPOSAL,
        sender="architect",
        recipient="reviewer",
        payload={
            "change_type": change_type,
            "target_file": target_file,
            "code_change": code_change,
            "rationale": rationale,
            "expected_score_impact": expected_score_impact,
            "rollback_plan": rollback_plan,
        },
    )


def make_revision(
    proposal_id: str,
    issues: list[str],
    suggestions: list[str],
) -> AgentMessage:
    """Reviewer → Architect: request revisions."""
    return AgentMessage(
        type=MessageType.REVISION_REQUEST,
        sender="reviewer",
        recipient="architect",
        payload={
            "proposal_id": proposal_id,
            "issues": issues,
            "suggestions": suggestions,
        },
    )


def make_approval(proposal_id: str, conditions: list[str] | None = None) -> AgentMessage:
    """Reviewer → Orchestrator: proposal approved."""
    return AgentMessage(
        type=MessageType.APPROVAL,
        sender="reviewer",
        recipient="orchestrator",
        payload={
            "proposal_id": proposal_id,
            "conditions": conditions or [],
        },
    )


def make_rejection(
    proposal_id: str,
    reason: str,
    blocked_types: list[str] | None = None,
) -> AgentMessage:
    """Reviewer → Orchestrator: proposal rejected."""
    return AgentMessage(
        type=MessageType.REJECTION,
        sender="reviewer",
        recipient="orchestrator",
        payload={
            "proposal_id": proposal_id,
            "reason": reason,
            "blocked_types": blocked_types or [],
        },
    )


def make_status(
    sender: str,
    status: str,
    details: dict[str, Any] | None = None,
) -> AgentMessage:
    """Any agent → Any: status report."""
    return AgentMessage(
        type=MessageType.STATUS_REPORT,
        sender=sender,
        recipient="",
        payload={
            "status": status,
            "details": details or {},
        },
    )