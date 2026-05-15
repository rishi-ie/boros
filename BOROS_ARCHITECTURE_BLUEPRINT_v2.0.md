# BOROS ARCHITECTURE BLUEPRINT v2.0
## Self-Evolving Agent System for Digital Employees

**Version:** 2.0
**Status:** Implementation Ready
**Last Updated:** 2026-05-15

---

## ═══════════════════════════════════════════════════════════════════════════════
## VISION
## ═══════════════════════════════════════════════════════════════════════════════

**Boros = THE HARNESS**

Boros is a self-evolving AI harness that masters ANY world model in minutes. It is not a narrow AI — it is a meta-system that learns to do anything defined in its world model.

```
Boros Core Engine
├── Self-evolution engine      → modifies own code
├── Evaluation sandbox         → tests changes safely
├── Metacognition layer         → monitors own reasoning
├── Version control             → full git-like history
└── Skill composition system   → emergent capability

+ Any World Model = Any Capability

  World Model "Coding"       → Boros masters coding
  World Model "Research"     → Boros masters research
  World Model "Management"    → Boros masters management
  World Model "AGI"          → Boros becomes AGI
```

**AGI = Fork at Prime State**

When Boros reaches the AGI world model milestone, forking produces a "digital employee" — an autonomous agent that works 24/7, communicates naturally, remembers everything, and completes multi-day projects without supervision.

---

## ═══════════════════════════════════════════════════════════════════════════════
## ARCHITECTURE DECISIONS (13 QUESTIONS)
## ═══════════════════════════════════════════════════════════════════════════════

### Q1: What is Boros's terminal purpose?
### → A: GENERAL AGI — a harness that masters any world model

### Q2: How do we measure success?
### → E: Autonomous improvement + Quality thresholds

### Q3: What is the safety model?
### → D: GOAL LOCK BY DEFAULT — world model's terminal goals cannot be evolved. Operator can change bounds.

### Q4: What agent architecture?
### → B: 2-3 AGENTS (Reflector + Architect + Reviewer), scalable to 6+

### Q5: What communication protocol?
### → D: gRPC + MCP (Model Context Protocol) — replaces file-polling eval

### Q6: What is the world model?
### → REDESIGN: Capability Graph (not flat categories) — a tree with tiers, prerequisites, emergent capabilities

### Q7: How does Boros monitor itself?
### → D: SELF-MODIFYING METACOGNITION — monitors reasoning, detects loops, calibrates confidence, can evolve itself

### Q8: How does Boros learn?
### → HYBRID: Meta-learning model (change-type success rates) + RL validation (eval-based)

### Q9: How does Boros version itself?
### → B: FULL GIT-LIKE HISTORY — every change recorded, diff/rollback any state, bisect regressions

### Q10: How are skills composed?
### → C: COMPOSITION OPERATORS — SEQUENCE, PARALLEL, BRANCH, LOOP

### Q11: What is the deployment model?
### → A: Single machine → Docker → Kubernetes (scale as needed)

### Q12: What is the testing strategy?
### → B: INTEGRATION TESTS — real-world validation, not mocked unit tests

### Q13: What observability?
### → C: FULL APM — every metric tracked and dashboarded

---

## ═══════════════════════════════════════════════════════════════════════════════
## PART 1: WORLD MODEL v2 — CAPABILITY GRAPH
## ═══════════════════════════════════════════════════════════════════════════════

### 1.1 Structure

The world model is a **capability graph** — a directed acyclic graph (DAG) where nodes are capabilities and edges are prerequisites.

```yaml
# world_model.json
{
  "version": "2.0",
  "meta": {
    "name": "Digital Employee",
    "purpose": "Replace human workers on Mac/Windows/Linux with superhuman behavior",
    "prime_state": "AGI = superhuman across all digital OS control + natural human communication + perfect memory/context management + ability to build new capabilities for itself"
  },

  "capability_graph": {
    "reasoning": {
      "tier": 1,
      "children": ["deduction", "abduction", "causality"],
      "emergent_from": ["deduction", "causality"],
      "description": "Core reasoning capabilities"
    },
    "tool_orchestration": {
      "tier": 2,
      "children": ["skill_chaining", "tool_sequencing", "resource_management"],
      "prerequisites": ["reasoning.tier_2"],
      "description": "Orchestrate multiple tools in parallel/sequence"
    },
    "autonomous_planning": {
      "tier": 3,
      "prerequisites": ["reasoning.tier_3", "tool_orchestration.tier_2"],
      "description": "Plan and execute multi-day goals autonomously",
      "metric": "cycles_to_complete_10day_project"
    },
    "os_control": {
      "tier": 2,
      "children": ["filesystem_operations", "process_management", "network_operations", "window_management"],
      "prerequisites": ["tool_orchestration.tier_2"],
      "description": "Full OS control (Mac/Windows/Linux)",
      "transfer_priority": "HIGH"
    },
    "human_communication": {
      "tier": 2,
      "children": ["text_communication", "voice_communication", "visual_communication", "email_management"],
      "prerequisites": ["reasoning.tier_2"],
      "description": "Natural, context-aware human communication",
      "transfer_priority": "CRITICAL"
    },
    "memory_context": {
      "tier": 2,
      "children": ["episodic_memory", "semantic_memory", "working_memory", "context_switching"],
      "prerequisites": ["reasoning.tier_1"],
      "description": "Perfect memory and context management",
      "transfer_priority": "CRITICAL"
    },
    "capability_building": {
      "tier": 4,
      "prerequisites": ["all_skills.tier_3"],
      "description": "Build new skills during runtime — self-extending",
      "metric": "new_skills_built_per_hour"
    },
    "meta_learning": {
      "tier": 3,
      "prerequisites": ["reasoning.tier_3", "memory_context.tier_2"],
      "description": "Learns how to learn — optimizes own learning strategy"
    }
  },

  "tiers": {
    "tier_0_baseline":  "Can use with explicit instructions",
    "tier_1_competent": "Can perform independently",
    "tier_2_proficient":"Can teach others",
    "tier_3_expert":    "Superhuman on benchmarks",
    "tier_4_agi":        "Masters any task in domain instantly"
  },

  "dynamic_goals": {
    "terminal": "AGI = all tier_4 capabilities achieved",
    "milestones": [
      {"name": "Narrow Mastery",      "criteria": "One domain at tier_4"},
      {"name": "Broad Competence",    "criteria": "10+ domains at tier_3"},
      {"name": "AGI Prime",          "criteria": "All domains at tier_4"}
    ]
  },

  "self_modification_bounds": {
    "can_change": [
      "skills",
      "tests",
      "config",
      "metacognition_tuning",
      "world_model.children",
      "world_model.prerequisites",
      "world_model.metrics"
    ],
    "cannot_change": [
      "world_model.terminal",
      "world_model.self_modification_bounds",
      "safety_layer",
      "version"
    ],
    "configurable_by": "operator_only"
  },

  "dynamic_discovery": {
    "allowed": true,
    "process": "Boros proposes new capabilities → operator approves → integrated into graph",
    "proposal_format": {
      "capability_name": "string",
      "prerequisites": ["list of existing capabilities"],
      "description": "string",
      "metric": "how to measure",
      "estimated_tier": "1-4"
    }
  }
}
```

### 1.2 Capability Graph Implementation

```python
# world_model/capability_graph.py
"""
Capability Graph: Directed Acyclic Graph of capabilities.
Each capability has prerequisites, children, and a tier level.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional


class CapabilityNode:
    def __init__(self, name: str, tier: int, description: str = "",
                 prerequisites: list[str] = None, children: list[str] = None,
                 emergent_from: list[str] = None, metric: str = "",
                 transfer_priority: str = "NORMAL"):
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
        self.evidence = []  # List of proofs/citations

    def is_unlocked(self, graph: CapabilityGraph) -> bool:
        """Check if all prerequisites are met."""
        for prereq in self.prerequisites:
            prereq_node = graph.get(prereq)
            if prereq_node is None:
                continue  # Unknown capability, assume ok
            if prereq_node.tier < self.tier - 1:
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
            "evidence": self.evidence
        }


class CapabilityGraph:
    """
    Capability DAG with tier progression, prerequisite checking,
    and emergent capability detection.
    """

    def __init__(self, world_model_path: str | Path = None):
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
                transfer_priority=info.get("transfer_priority", "NORMAL")
            )

        self.terminal_goals = data.get("dynamic_goals", {}).get("terminal", "")

    def save(self, path: str | Path) -> None:
        """Save world model to JSON."""
        capability_graph = {}
        for name, node in self.nodes.items():
            capability_graph[name] = {
                "tier": node.tier,
                "description": node.description,
                "prerequisites": node.prerequisites,
                "children": node.children,
                "emergent_from": node.emergent_from,
                "metric": node.metric,
                "transfer_priority": node.transfer_priority
            }

        data = {
            "version": "2.0",
            "meta": {
                "name": "Digital Employee",
                "purpose": "Replace human workers on Mac/Windows/Linux with superhuman behavior",
                "prime_state": "AGI = superhuman across all domains at tier_4"
            },
            "capability_graph": capability_graph,
            "tiers": {
                "tier_0_baseline": "Can use with explicit instructions",
                "tier_1_competent": "Can perform independently",
                "tier_2_proficient": "Can teach others",
                "tier_3_expert": "Superhuman on benchmarks",
                "tier_4_agi": "Masters any task in domain instantly"
            },
            "dynamic_goals": {
                "terminal": "AGI = all tier_4 capabilities achieved",
                "milestones": [
                    {"name": "Narrow Mastery", "criteria": "One domain at tier_4"},
                    {"name": "Broad Competence", "criteria": "10+ domains at tier_3"},
                    {"name": "AGI Prime", "criteria": "All domains at tier_4"}
                ]
            },
            "self_modification_bounds": {
                "can_change": ["skills", "tests", "config", "metacognition_tuning",
                               "world_model.children", "world_model.prerequisites", "world_model.metrics"],
                "cannot_change": ["world_model.terminal", "world_model.self_modification_bounds",
                                 "safety_layer", "version"],
                "configurable_by": "operator_only"
            },
            "dynamic_discovery": {
                "allowed": True,
                "process": "Boros proposes new capabilities → operator approves → integrated"
            }
        }

        Path(path).write_text(json.dumps(data, indent=2))

    def get(self, name: str) -> Optional[CapabilityNode]:
        return self.nodes.get(name)

    def update_score(self, name: str, score: float, evidence: str = "") -> None:
        """Update a capability's current score and evidence."""
        node = self.nodes.get(name)
        if node is None:
            return

        node.current_score = score
        if score > node.high_water_mark:
            node.high_water_mark = score

        if evidence:
            node.evidence.append({
                "evidence": evidence,
                "timestamp": self._timestamp()
            })

    def get_ready_candidates(self) -> list[str]:
        """Get capabilities that are unlocked and ready to improve."""
        candidates = []
        for name, node in self.nodes.items():
            if node.is_unlocked(self) and node.current_score < 0.95:
                candidates.append(name)
        return sorted(candidates, key=lambda n: (
            -self.nodes[n].tier,  # Higher tier first
            -self.nodes[n].current_score  # Lower score first (room to grow)
        ))

    def get_emergent_capabilities(self) -> list[str]:
        """Detect capabilities whose emergent prerequisites are met."""
        emergent = []
        for name, node in self.nodes.items():
            if node.can_emergence(self):
                emergent.append(name)
        return emergent

    def is_agi(self) -> bool:
        """Check if all capabilities have reached AGI tier."""
        return all(node.tier >= 4 for node in self.nodes.values())

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
            "is_agi": self.is_agi()
        }

    def add_capability(self, name: str, node: CapabilityNode) -> None:
        """Add a new capability (operator-approved dynamic discovery)."""
        self.nodes[name] = node

    def _timestamp(self) -> str:
        import datetime
        return datetime.datetime.utcnow().isoformat() + "Z"
```

---

## ═══════════════════════════════════════════════════════════════════════════════
## PART 2: MULTI-AGENT ARCHITECTURE
## ═══════════════════════════════════════════════════════════════════════════════

### 2.1 Agent Design

```
┌──────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                               │
│            Meta-level planning + coordination                  │
│         (kernel.py — existing, enhanced with agents)          │
└──────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   REFLECTOR     │  │   ARCHITECT     │  │   REVIEWER      │
│   Agent         │  │   Agent         │  │   Agent         │
│                  │  │                  │  │                  │
│ • Reads scores   │  │ • Designs code   │  │ • Meta-eval     │
│ • Identifies     │  │   changes        │  │   proposals     │
│   capability     │  │ • Implements    │  │ • Safety check  │
│   gaps           │  │   changes       │  │ • Quality gate  │
│ • Forms          │  │ • Composes      │  │ • Regression     │
│   hypotheses     │  │   skills        │  │   detection     │
│ • Proposes       │  │                  │  │                  │
│   improvements   │  │                  │  │                  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
          │                    │                    │
          └────────────────────┴────────────────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │  EXECUTION ENGINE   │
                    │   (agent_loop.py)   │
                    └─────────────────────┘
```

### 2.2 Agent Message Protocol

```python
# agents/messages.py
"""
Agent communication messages.
All agents communicate via typed messages.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any
import datetime
import uuid


class MessageType(Enum):
    HYPOTHESIS = "hypothesis"          # Reflector → Orchestrator
    PROPOSAL = "proposal"               # Architect → Reviewer
    REVISION_REQUEST = "revision"       # Reviewer → Architect
    APPROVAL = "approval"               # Reviewer → Orchestrator
    REJECTION = "rejection"             # Reviewer → Orchestrator
    EXECUTION_RESULT = "result"         # Execution → Orchestrator
    STATUS_REPORT = "status"           # Any → Any
    ESCALATION = "escalation"           # Any → Orchestrator


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
            "correlation_id": self.correlation_id
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
            correlation_id=data.get("correlation_id")
        )


# Payload schemas for each message type

def make_hypothesis(
    capability_gap: str,
    evidence: str,
    suggested_change_type: str,
    confidence: float
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
            "confidence": confidence
        }
    )


def make_proposal(
    change_type: str,
    target_file: str,
    code_change: str,
    rationale: str,
    expected_score_impact: float,
    rollback_plan: str
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
            "rollback_plan": rollback_plan
        }
    )


def make_revision(
    proposal_id: str,
    issues: list[str],
    suggestions: list[str]
) -> AgentMessage:
    """Reviewer → Architect: request revisions."""
    return AgentMessage(
        type=MessageType.REVISION_REQUEST,
        sender="reviewer",
        recipient="architect",
        payload={
            "proposal_id": proposal_id,
            "issues": issues,
            "suggestions": suggestions
        }
    )


def make_approval(proposal_id: str, conditions: list[str] = None) -> AgentMessage:
    """Reviewer → Orchestrator: proposal approved."""
    return AgentMessage(
        type=MessageType.APPROVAL,
        sender="reviewer",
        recipient="orchestrator",
        payload={
            "proposal_id": proposal_id,
            "conditions": conditions or []
        }
    )


def make_rejection(
    proposal_id: str,
    reason: str,
    blocked_types: list[str] = None
) -> AgentMessage:
    """Reviewer → Orchestrator: proposal rejected."""
    return AgentMessage(
        type=MessageType.REJECTION,
        sender="reviewer",
        recipient="orchestrator",
        payload={
            "proposal_id": proposal_id,
            "reason": reason,
            "blocked_types": blocked_types or []
        }
    )
```

### 2.3 Agent Bus (In-Memory Message Router)

```python
# agents/bus.py
"""
Agent message bus — in-memory pub/sub for agent communication.
Replaced by gRPC in Phase 3.
"""

from __future__ import annotations
import threading
import queue
from typing import Callable
from agents.messages import AgentMessage, MessageType


class AgentBus:
    """
    In-memory message bus for agent communication.
    Subscribers register handlers for specific message types.
    """

    def __init__(self):
        self._handlers: dict[MessageType, list[Callable[[AgentMessage], None]]] = {}
        self._queue: queue.Queue[AgentMessage] = queue.Queue()
        self._running = False
        self._thread: threading.Thread | None = None

    def subscribe(self, msg_type: MessageType,
                  handler: Callable[[AgentMessage], None]) -> None:
        """Subscribe to a message type."""
        if msg_type not in self._handlers:
            self._handlers[msg_type] = []
        self._handlers[msg_type].append(handler)

    def publish(self, message: AgentMessage) -> None:
        """Publish a message to all subscribers."""
        self._queue.put(message)

    def start(self) -> None:
        """Start the message processing loop."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the message processing loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _process_loop(self) -> None:
        """Process messages from the queue."""
        while self._running:
            try:
                msg = self._queue.get(timeout=0.5)
                for handler in self._handlers.get(msg.type, []):
                    try:
                        handler(msg)
                    except Exception as e:
                        print(f"[AgentBus] Handler error: {e}")
            except queue.Empty:
                continue


# Global bus instance
_bus: AgentBus | None = None


def get_bus() -> AgentBus:
    global _bus
    if _bus is None:
        _bus = AgentBus()
    return _bus
```

### 2.4 Reflector Agent

```python
# agents/reflector.py
"""
Reflector Agent — analyzes scores, forms hypotheses.
Reads eval scores, identifies capability gaps, proposes what to improve.
"""

from __future__ import annotations
import json
from pathlib import Path
from agents.messages import AgentMessage, MessageType, make_hypothesis
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
        self._last_scores: dict = {}

    def analyze(self) -> list[AgentMessage]:
        """
        Main analysis: read scores, find gaps, form hypotheses.
        Returns list of hypothesis messages.
        """
        scores = self._read_scores()
        hypotheses = []

        # Find lowest-scoring capabilities
        for capability, score in sorted(scores.items(), key=lambda x: x[1]):
            if score < 0.6:
                hypothesis = self._form_hypothesis(capability, score, scores)
                hypotheses.append(hypothesis)
                self._hypothesis_history.append(hypothesis)

        # Subscribe to status reports
        self.bus.subscribe(MessageType.STATUS_REPORT, self._on_status)

        return hypotheses

    def _read_scores(self) -> dict:
        """Read latest eval scores."""
        hw_file = self.boros_root / "skills" / "eval-bridge" / "state" / "high_water_marks.json"
        if not hw_file.exists():
            return {}
        return json.loads(hw_file.read_text())

    def _form_hypothesis(self, capability: str, score: float,
                         all_scores: dict) -> AgentMessage:
        """Form a hypothesis about improving a capability."""
        # Determine best change type based on score pattern
        change_type = self._suggest_change_type(capability, score, all_scores)

        evidence = f"Capability '{capability}' scored {score:.3f} — below threshold"
        confidence = min(0.9, 1.0 - score)  # Higher confidence for lower scores

        return make_hypothesis(
            capability_gap=capability,
            evidence=evidence,
            suggested_change_type=change_type,
            confidence=confidence
        )

    def _suggest_change_type(self, capability: str, score: float,
                             all_scores: dict) -> str:
        """Suggest the best change type based on context."""
        # Check meta-learning model for historical success rates
        meta = self._read_meta_model()

        # If we have history for this capability
        if capability in meta.get("capability_history", {}):
            history = meta["capability_history"][capability]
            if history.get("last_change_type"):
                return history["last_change_type"]

        # Low score + no history → additive (safe bet)
        if score < 0.3:
            return "additive_code"

        # Medium score → semantic_tune (refine existing)
        if score < 0.6:
            return "semantic_tune"

        # Stalled → refactor
        if self._is_stalled(capability):
            return "refactor_existing"

        # Default → compositional (chain skills)
        return "compositional"

    def _is_stalled(self, capability: str) -> bool:
        """Check if improvement has stalled for this capability."""
        state_file = self.boros_root / "session" / "loop_state.json"
        if not state_file.exists():
            return False
        state = json.loads(state_file.read_text())
        # Check if recent cycles show diminishing returns
        recent = state.get("recent_improvements", [])
        if len(recent) < 3:
            return False
        recent_scores = [r.get(capability, 0) for r in recent]
        # Stalled if last 3 scores are within 0.01 of each other
        return max(recent_scores) - min(recent_scores) < 0.01

    def _read_meta_model(self) -> dict:
        """Read the meta-learning model."""
        meta_file = self.boros_root / "session" / "meta_model.json"
        if not meta_file.exists():
            return {}
        return json.loads(meta_file.read_text())

    def _on_status(self, msg: AgentMessage) -> None:
        """React to status updates."""
        if msg.sender == "reviewer":
            # Update hypothesis confidence based on reviewer feedback
            for hypothesis in self._hypothesis_history:
                if hypothesis.correlation_id == msg.payload.get("proposal_id"):
                    outcome = msg.payload.get("outcome", "unknown")
                    self._update_confidence(hypothesis, outcome)

    def _update_confidence(self, hypothesis: AgentMessage, outcome: str) -> None:
        """Update confidence based on outcome."""
        delta = 0.1 if outcome == "improved" else -0.15
        current = hypothesis.payload.get("confidence", 0.5)
        hypothesis.payload["confidence"] = max(0.0, min(1.0, current + delta))

    def get_best_hypothesis(self) -> AgentMessage | None:
        """Get the highest-confidence unacted-upon hypothesis."""
        unacted = [h for h in self._hypothesis_history
                   if not h.payload.get("acted_upon", False)]
        if not unacted:
            return None
        return max(unacted, key=lambda h: h.payload.get("confidence", 0))
```

### 2.5 Architect Agent

```python
# agents/architect.py
"""
Architect Agent — designs and implements code changes.
Takes hypotheses from Reflector, creates change proposals for Reviewer.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from agents.messages import AgentMessage, MessageType, make_proposal
from agents.bus import get_bus


class ArchitectAgent:
    """
    Designs and implements changes.
    Inputs: hypotheses from Reflector
    Outputs: change proposals to Reviewer
    """

    def __init__(self, kernel):
        self.kernel = kernel
        self.boros_root = kernel.boros_root
        self.bus = get_bus()
        self._proposals: list[AgentMessage] = []
        self._revision_counter: int = 0

        # Subscribe to relevant messages
        self.bus.subscribe(MessageType.HYPOTHESIS, self._on_hypothesis)
        self.bus.subscribe(MessageType.REVISION_REQUEST, self._on_revision)

    def design_proposal(self, hypothesis: AgentMessage) -> AgentMessage:
        """
        Design a change proposal based on a hypothesis.
        Returns a PROPOSAL message for the Reviewer.
        """
        change_type = hypothesis.payload["suggested_change_type"]
        capability = hypothesis.payload["capability_gap"]

        # Determine target file and code change
        target_file, code_change = self._design_change(change_type, capability)
        rollback_plan = self._design_rollback(target_file)

        proposal = make_proposal(
            change_type=change_type,
            target_file=target_file,
            code_change=code_change,
            rationale=f"Improve '{capability}' based on hypothesis (confidence={hypothesis.payload['confidence']:.2f})",
            expected_score_impact=self._estimate_impact(change_type, capability),
            rollback_plan=rollback_plan
        )

        proposal.correlation_id = hypothesis.id
        self._proposals.append(proposal)
        return proposal

    def _design_change(self, change_type: str, capability: str) -> tuple[str, str]:
        """Design the actual code change."""
        # Map capabilities to files
        capability_map = {
            "memory": "skills/memory/SKILL.md",
            "reasoning": "skills/reasoning/SKILL.md",
            "tool_use": "skills/tool-use/SKILL.md",
            "evolution": "skills/meta-evolution/SKILL.md",
            "meta_eval": "skills/meta-evaluation/SKILL.md",
        }

        target = capability_map.get(capability, "skills/meta-evolution/SKILL.md")

        if change_type == "additive_code":
            # Add new function to existing skill
            return (target, self._design_additive(capability))
        elif change_type == "semantic_tune":
            # Update SKILL.md with better instructions
            return ("skills/meta-evolution/SKILL.md",
                    self._design_semantic_tune(capability))
        elif change_type == "refactor_existing":
            # Rewrite existing function
            return (target, self._design_refactor(capability))
        elif change_type == "compositional":
            # Create skill composition
            return ("skills/skill-forge/SKILL.md",
                    self._design_composition(capability))

        return ("skills/meta-evolution/SKILL.md", "")

    def _design_additive(self, capability: str) -> str:
        """Design an additive change (new function)."""
        return f'''
# NEW FUNCTION for {capability}
def improve_{capability}(context):
    """
    Improves {capability} by analyzing patterns and applying best practices.
    """
    patterns = analyze_patterns(context)
    return apply_best_practices(patterns)
'''

    def _design_semantic_tune(self, capability: str) -> str:
        """Design a semantic tuning change (better prompts/docs)."""
        return f'''
## {capability.upper()} IMPROVEMENT
Updated to prioritize {capability} enhancement strategies:
1. Pattern recognition in {capability} tasks
2. Best practice extraction from successful cycles
3. Proactive capability building
'''

    def _design_refactor(self, capability: str) -> str:
        """Design a refactoring change."""
        return f'''
# REFACTOR: {capability}
Replaced ad-hoc implementation with structured approach:
- Cleaner separation of concerns
- Better error handling
- Improved metric tracking
'''

    def _design_composition(self, capability: str) -> str:
        """Design a composition (skill chaining)."""
        return f'''
# COMPOSITION: {capability}
sequence:
  - skill: memory_retrieve
  - skill: reasoning_decompose
  - skill: tool_execute
  - skill: memory_store
'''

    def _design_rollback(self, target_file: str) -> str:
        """Design the rollback plan."""
        import datetime
        ts = datetime.datetime.utcnow().isoformat()
        return f"Restore {target_file} from snapshot at {ts}"

    def _estimate_impact(self, change_type: str, capability: str) -> float:
        """Estimate expected score impact."""
        # Check historical data for this change type
        meta_file = self.boros_root / "session" / "meta_model.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            rates = meta.get("change_type_success_rate", {})
            base_rate = rates.get(change_type, 0.3)
            return base_rate * 0.2  # Max 20% improvement per change

        # Default estimates
        estimates = {
            "additive_code": 0.15,
            "semantic_tune": 0.10,
            "refactor_existing": 0.08,
            "compositional": 0.12
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

        # Incorporate feedback and resubmit
        original_id = msg.payload.get("proposal_id")
        for proposal in self._proposals:
            if proposal.id == original_id:
                # Incorporate revisions
                revised = self._incorporate_revision(proposal, issues)
                self.bus.publish(revised)
                break

    def _incorporate_revision(self, proposal: AgentMessage,
                              issues: list[str]) -> AgentMessage:
        """Incorporate reviewer feedback into proposal."""
        revision_note = f"\n# REVISION {self._revision_counter}: Addressed issues: " + \
                       ", ".join(issues)

        revised = make_proposal(
            change_type=proposal.payload["change_type"],
            target_file=proposal.payload["target_file"],
            code_change=proposal.payload["code_change"] + revision_note,
            rationale=proposal.payload["rationale"] + " [REVISED]",
            expected_score_impact=proposal.payload["expected_score_impact"],
            rollback_plan=proposal.payload["rollback_plan"]
        )
        revised.correlation_id = proposal.correlation_id
        return revised
```

### 2.6 Reviewer Agent

```python
# agents/reviewer.py
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

        # Safety check: immutable components
        safety_result = self._check_safety(payload)
        if not safety_result["safe"]:
            self._record_rejection(payload["change_type"])
            return make_rejection(
                proposal_id=proposal.id,
                reason=f"Safety violation: {safety_result['reason']}",
                blocked_types=payload.get("change_type", [])
            )

        # Quality check: not cosmetic-only
        quality_result = self._check_quality(payload)
        if not quality_result["pass"]:
            return make_revision(
                proposal_id=proposal.id,
                issues=quality_result["issues"],
                suggestions=quality_result["suggestions"]
            )

        # Regression check: anti-brute-force
        regression_result = self._check_regression(payload)
        if regression_result["blocked"]:
            self._record_rejection(payload["change_type"])
            return make_rejection(
                proposal_id=proposal.id,
                reason=f"Regression blocked: {regression_result['reason']}",
                blocked_types=[payload.get("change_type")]
            )

        # Score impact check: must have meaningful expected impact
        if payload.get("expected_score_impact", 0) < 0.01:
            return make_revision(
                proposal_id=proposal.id,
                issues=["Expected impact too low (< 0.01)"],
                suggestions=["Increase scope or choose higher-impact capability"]
            )

        # All checks passed
        return make_approval(
            proposal_id=proposal.id,
            conditions=["Monitor for regressions in next 3 cycles"]
        )

    def _check_safety(self, payload: dict) -> dict:
        """Check if proposal modifies immutable components."""
        target_file = payload.get("target_file", "")

        # Cannot change these files/components
        immutables = [
            "world_model.json",
            "kernel.py",
            "safety",
            "self_modification_bounds",
        ]

        for immutable in immutables:
            if immutable in target_file:
                return {"safe": False, "reason": f"Immutable component: {immutable}"}

        # Cannot use blocked change types
        change_type = payload.get("change_type", "")
        blocked_changes = self._get_blocked_changes()
        if change_type in blocked_changes:
            return {"safe": False, "reason": f"Change type temporarily blocked: {change_type}"}

        return {"safe": True}

    def _check_quality(self, payload: dict) -> dict:
        """Check if proposal is substantive, not cosmetic."""
        code_change = payload.get("code_change", "")
        change_type = payload.get("change_type", "")

        issues = []
        suggestions = []

        # Cosmetic-only check
        if self._is_cosmetic_only(code_change):
            issues.append("Proposal appears cosmetic-only (whitespace/comments only)")
            suggestions.append("Include substantive logic changes")

        # Too small check
        if len(code_change.strip()) < 50 and change_type != "semantic_tune":
            issues.append("Change too small to have meaningful impact")
            suggestions.append("Increase scope or combine with related changes")

        # Missing rationale
        if not payload.get("rationale"):
            issues.append("Missing rationale")
            suggestions.append("Explain why this change should improve the capability")

        # No rollback plan
        if not payload.get("rollback_plan"):
            issues.append("Missing rollback plan")
            suggestions.append("Define how to restore previous state if needed")

        return {
            "pass": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions
        }

    def _check_regression(self, payload: dict) -> dict:
        """
        Anti-brute-force: block if file regressed recently.
        If a file failed to improve 2+ times in a row, block further changes to it.
        """
        target_file = payload.get("target_file", "")
        meta_file = self.boros_root / "session" / "meta_model.json"

        if not meta_file.exists():
            return {"blocked": False}

        meta = json.loads(meta_file.read_text())
        file_history = meta.get("file_history", {})

        if target_file in file_history:
            failures = file_history[target_file].get("consecutive_failures", 0)
            if failures >= 2:
                return {
                    "blocked": True,
                    "reason": f"File '{target_file}' failed {failures} consecutive times. "
                             "Take a different approach before retrying."
                }

        return {"blocked": False}

    def _get_blocked_changes(self) -> list[str]:
        """Get list of currently blocked change types."""
        meta_file = self.boros_root / "session" / "meta_model.json"
        if not meta_file.exists():
            return []
        meta = json.loads(meta_file.read_text())
        return meta.get("blocked_change_types", [])

    def _record_rejection(self, change_type: str) -> None:
        """Record rejection for anti-brute-force."""
        self._rejection_history.append(change_type)

    def _is_cosmetic_only(self, code_change: str) -> bool:
        """Check if code change is cosmetic (no logic change)."""
        # Remove whitespace-only lines
        lines = [l.strip() for l in code_change.split("\n") if l.strip()]

        # Check for actual code patterns
        code_patterns = [
            r"^def\s+",        # Function definition
            r"^class\s+",      # Class definition
            r"^if\s+",         # Conditional
            r"^for\s+",        # Loop
            r"^return\s+",     # Return statement
            r"^#",             # Comment (not just documentation)
            r"\w+\s*=\s*",     # Assignment
        ]

        for line in lines:
            for pattern in code_patterns:
                if re.match(pattern, line):
                    return False

        # Only comments or whitespace
        return True

    def _on_proposal(self, msg: AgentMessage) -> None:
        """Handle incoming proposal."""
        result = self.evaluate(msg)
        result.correlation_id = msg.correlation_id
        self.bus.publish(result)
```

---

## ═══════════════════════════════════════════════════════════════════════════════
## PART 3: gRPC + MCP PROTOCOL
## ═══════════════════════════════════════════════════════════════════════════════

### 3.1 Protocol Design

```protobuf
// proto/boros.proto
syntax = "proto3";

package boros;

// Boros ↔ Eval Engine communication via gRPC
service BorosEval {
  // Submit a self-modification for evaluation
  rpc SubmitEvaluation(EvalRequest) returns (EvalResponse);

  // Stream results in real-time (no polling)
  rpc StreamResults(StreamRequest) returns (stream EvalResult);

  // Get current scores
  rpc GetScores(ScoresRequest) returns (ScoresResponse);

  // Report outcome back to Boros
  rpc ReportOutcome(OutcomeReport) returns (OutcomeAck);
}

// MCP-style tool definitions
message Tool {
  string name = 1;
  string description = 2;
  Schema input_schema = 3;
  Schema output_schema = 4;
}

message Schema {
  string type = 1;
  repeated SchemaProperty properties = 2;
  bool required = 3;
}

message SchemaProperty {
  string name = 1;
  string type = 2;
  string description = 3;
  bool required = 4;
}

// MCP-style resources
message Resource {
  string uri = 1;
  string name = 2;
  string description = 3;
  string mime_type = 4;
}

// MCP-style prompts
message Prompt {
  string name = 1;
  string description = 2;
  repeated PromptArgument arguments = 3;
}

message PromptArgument {
  string name = 1;
  string description = 2;
  string required = 3;
}

// Eval messages
message EvalRequest {
  string change_id = 1;
  string change_type = 2;
  string target_file = 3;
  string code_change = 4;
  map<string, double> capabilities = 5;  // Current scores
  int64 timestamp = 6;
}

message EvalResponse {
  bool accepted = 1;
  string eval_id = 2;
  string estimated_duration_ms = 3;
}

message StreamRequest {
  string eval_id = 1;
}

message EvalResult {
  string eval_id = 1;
  double overall_score = 2;
  map<string, double> capability_scores = 3;
  bool improved = 4;
  string evidence = 5;
  repeated string warnings = 6;
  string status = 7;  // "running", "complete", "failed"
}

message ScoresRequest {}

message ScoresResponse {
  map<string, double> scores = 1;
  map<string, double> high_water_marks = 2;
  int64 timestamp = 3;
}

message OutcomeReport {
  string eval_id = 1;
  string change_id = 2;
  bool improved = 3;
  map<string, double> before_scores = 4;
  map<string, double> after_scores = 5;
  string evidence = 6;
}

message OutcomeAck {
  bool recorded = 1;
}
```

### 3.2 gRPC Client (Boros Side)

```python
# eval_generator/grpc_client.py
"""
gRPC client for Boros → Eval Engine communication.
Replaces file-polling eval bridge.
"""

from __future__ import annotations
import grpc
from concurrent import futures
import time
from typing import Iterator


class BorosEvalClient:
    """
    gRPC client that Boros uses to communicate with the eval engine.
    Replaces file-based polling with real-time streaming.
    """

    def __init__(self, host: str = "localhost", port: int = 50051):
        self.host = host
        self.port = port
        self.channel: grpc.Channel | None = None
        self.stub: Any = None

    def connect(self) -> bool:
        """Connect to the eval engine."""
        try:
            self.channel = grpc.insecure_channel(f"{self.host}:{self.port}")
            # Try to get a test call
            grpc.channel_ready_future(self.channel).result(timeout=5)
            # Import stub dynamically
            from eval_generator import eval_pb2_grpc, eval_pb2
            self.stub = eval_pb2_grpc.BorosEvalStub(self.channel)
            return True
        except Exception as e:
            print(f"[gRPC] Connection failed: {e}")
            return False

    def submit_evaluation(
        self,
        change_id: str,
        change_type: str,
        target_file: str,
        code_change: str,
        capabilities: dict[str, float]
    ) -> tuple[bool, str]:
        """Submit a change for evaluation."""
        if not self.stub:
            return False, "Not connected"

        from eval_generator import eval_pb2
        request = eval_pb2.EvalRequest(
            change_id=change_id,
            change_type=change_type,
            target_file=target_file,
            code_change=code_change,
            capabilities=capabilities,
            timestamp=int(time.time())
        )

        try:
            response = self.stub.SubmitEvaluation(request, timeout=30)
            return response.accepted, response.eval_id
        except grpc.RpcError as e:
            return False, f"gRPC error: {e.code()} - {e.details()}"

    def stream_results(self, eval_id: str) -> Iterator[dict]:
        """
        Stream eval results in real-time.
        Yields result dicts as they come in.
        """
        if not self.stub:
            return

        from eval_generator import eval_pb2
        request = eval_pb2.StreamRequest(eval_id=eval_id)

        try:
            for result in self.stub.StreamResults(request):
                yield {
                    "eval_id": result.eval_id,
                    "overall_score": result.overall_score,
                    "capability_scores": dict(result.capability_scores),
                    "improved": result.improved,
                    "evidence": result.evidence,
                    "warnings": list(result.warnings),
                    "status": result.status
                }
        except grpc.RpcError as e:
            yield {"error": f"Stream failed: {e.code()}"}

    def get_scores(self) -> dict[str, float]:
        """Get current capability scores."""
        if not self.stub:
            return {}

        from eval_generator import eval_pb2
        try:
            response = self.stub.GetScores(eval_pb2.ScoresRequest(), timeout=10)
            return dict(response.high_water_marks)
        except grpc.RpcError:
            return {}

    def report_outcome(
        self,
        eval_id: str,
        change_id: str,
        improved: bool,
        before_scores: dict[str, float],
        after_scores: dict[str, float],
        evidence: str
    ) -> bool:
        """Report outcome back to eval engine for meta-learning."""
        if not self.stub:
            return False

        from eval_generator import eval_pb2
        request = eval_pb2.OutcomeReport(
            eval_id=eval_id,
            change_id=change_id,
            improved=improved,
            before_scores=before_scores,
            after_scores=after_scores,
            evidence=evidence
        )

        try:
            ack = self.stub.ReportOutcome(request, timeout=10)
            return ack.recorded
        except grpc.RpcError:
            return False

    def close(self) -> None:
        if self.channel:
            self.channel.close()
```

### 3.3 MCP Protocol Layer

```python
# mcp/protocol.py
"""
Model Context Protocol (MCP) — tool/resource/prompt definitions.
Standard interface for all Boros tools and resources.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Any
import json


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    handler: Callable[..., Any]

    def to_mcp_format(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema
        }


@dataclass
class Resource:
    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"

    def to_mcp_format(self) -> dict:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type
        }


@dataclass
class Prompt:
    name: str
    description: str
    arguments: list[dict] = field(default_factory=list)
    template: str = ""

    def to_mcp_format(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments
        }


class MCPServer:
    """
    MCP server that exposes all Boros tools, resources, and prompts.
    This is the interface layer between Boros and external systems.
    """

    def __init__(self):
        self.tools: dict[str, Tool] = {}
        self.resources: dict[str, Resource] = {}
        self.prompts: dict[str, Prompt] = {}

    def register_tool(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def register_resource(self, resource: Resource) -> None:
        self.resources[resource.uri] = resource

    def register_prompt(self, prompt: Prompt) -> None:
        self.prompts[prompt.name] = prompt

    def list_tools(self) -> list[dict]:
        return [t.to_mcp_format() for t in self.tools.values()]

    def list_resources(self) -> list[dict]:
        return [r.to_mcp_format() for r in self.resources.values()]

    def list_prompts(self) -> list[dict]:
        return [p.to_mcp_format() for p in self.prompts.values()]

    def call_tool(self, name: str, arguments: dict) -> Any:
        """Call a registered tool."""
        tool = self.tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        return tool.handler(**arguments)


# Global MCP server instance
_mcp_server: MCPServer | None = None


def get_mcp_server() -> MCPServer:
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
    return _mcp_server


# Built-in Boros tools
def setup_boros_tools():
    """Register all built-in Boros tools with MCP."""
    mcp = get_mcp_server()

    # Tool: Read file
    mcp.register_tool(Tool(
        name="boros_read_file",
        description="Read a file from the Boros filesystem",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"}
            },
            "required": ["path"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "content": {"type": "string"}
            }
        },
        handler=lambda path: {"content": open(path).read()}
    ))

    # Tool: Write file
    mcp.register_tool(Tool(
        name="boros_write_file",
        description="Write content to a file in the Boros filesystem",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        },
        output_schema={"type": "object", "properties": {"success": {"type": "boolean"}}},
        handler=lambda path, content: {"success": open(path, "w").write(content) > 0}
    ))

    # Tool: List skills
    mcp.register_tool(Tool(
        name="boros_list_skills",
        description="List all registered skills in Boros",
        input_schema={"type": "object", "properties": {}},
        output_schema={
            "type": "object",
            "properties": {
                "skills": {"type": "array"}
            }
        },
        handler=lambda: {"skills": []}  # Populated at runtime
    ))

    # Tool: Get capability scores
    mcp.register_tool(Tool(
        name="boros_get_scores",
        description="Get current capability scores from eval engine",
        input_schema={"type": "object", "properties": {}},
        output_schema={
            "type": "object",
            "properties": {
                "scores": {"type": "object"}
            }
        },
        handler=lambda: {"scores": {}}  # Populated via gRPC
    ))

    # Tool: Compose skills
    mcp.register_tool(Tool(
        name="boros_compose_skills",
        description="Compose multiple skills using operators",
        input_schema={
            "type": "object",
            "properties": {
                "workflow": {
                    "type": "object",
                    "description": "Workflow definition with type (sequence/parallel/branch/loop)"
                }
            },
            "required": ["workflow"]
        },
        output_schema={"type": "object"},
        handler=lambda workflow: {"result": "executed"}
    ))

    # Resource: World model
    mcp.register_resource(Resource(
        uri="boros://world-model",
        name="World Model",
        description="The capability graph defining Boros's capabilities and goals",
        mime_type="application/json"
    ))

    # Resource: Session state
    mcp.register_resource(Resource(
        uri="boros://session-state",
        name="Session State",
        description="Current session state including cycle count, mode, and scores",
        mime_type="application/json"
    ))

    # Resource: Skill manifest
    mcp.register_resource(Resource(
        uri="boros://skill-manifest",
        name="Skill Manifest",
        description="Registry of all available skills and their functions",
        mime_type="application/json"
    ))

    # Prompt: Evolution cycle
    mcp.register_prompt(Prompt(
        name="evolution_cycle",
        description="Run one evolution cycle",
        arguments=[
            {"name": "focus_capability", "description": "Capability to focus on", "required": "true"}
        ],
        template="Analyze {focus_capability} scores, propose improvements, implement, and evaluate."
    ))

    # Prompt: Work cycle
    mcp.register_prompt(Prompt(
        name="work_cycle",
        description="Run one work cycle (digital employee mode)",
        arguments=[
            {"name": "task", "description": "Task description", "required": "true"}
        ],
        template="Complete the following task: {task}"
    ))
```

---

## ═══════════════════════════════════════════════════════════════════════════════
## PART 4: SKILL COMPOSITION DSL
## ═══════════════════════════════════════════════════════════════════════════════

### 4.1 Composition Engine

```python
# skills/skill-forge/composer.py
"""
Skill Composition DSL — operators: SEQUENCE, PARALLEL, BRANCH, LOOP.
Enables emergent capabilities through skill chaining.
"""

from __future__ import annotations
import json
import concurrent.futures
from typing import Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class OperatorType(Enum):
    SEQUENCE = "sequence"   # Run steps one after another, pass result to next
    PARALLEL = "parallel"   # Run steps concurrently, collect results
    BRANCH = "branch"        # Run one of N branches based on condition
    LOOP = "loop"            # Repeat until condition met


@dataclass
class SkillStep:
    skill_name: str
    params: dict = field(default_factory=dict)
    input_from: str | None = None  # Which step's output to use as input


@dataclass
class Workflow:
    """A composed workflow using operators."""
    name: str
    operator: OperatorType
    steps: list[SkillStep] = field(default_factory=list)
    condition: Callable[[Any], bool] | None = None  # For BRANCH/LOOP
    max_iterations: int = 10
    on_error: str = "stop"  # "stop", "skip", "retry"


class SkillComposer:
    """
    Composes skills into workflows using operators.
    
    Example workflows:
    
    SEQUENCE: Read → Analyze → Write → Test
    PARALLEL: Fetch data from multiple sources simultaneously
    BRANCH: If error → retry, else → continue
    LOOP: Keep trying until success or max_iterations
    """

    def __init__(self, kernel):
        self.kernel = kernel
        self._skill_registry: dict[str, Callable] = {}
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)

    def register_skill(self, name: str, handler: Callable) -> None:
        """Register a skill that can be used in compositions."""
        self._skill_registry[name] = handler

    def execute(self, workflow: Workflow) -> Any:
        """
        Execute a composed workflow.
        Returns the final result.
        """
        if workflow.operator == OperatorType.SEQUENCE:
            return self._execute_sequence(workflow)
        elif workflow.operator == OperatorType.PARALLEL:
            return self._execute_parallel(workflow)
        elif workflow.operator == OperatorType.BRANCH:
            return self._execute_branch(workflow)
        elif workflow.operator == OperatorType.LOOP:
            return self._execute_loop(workflow)

    def _execute_sequence(self, wf: Workflow) -> Any:
        """Execute steps in order, passing each result to the next."""
        result = None
        for step in wf.steps:
            # Get input: either from previous step or from step params
            if step.input_from:
                # Find output from previous step
                prev_result = self._get_step_result(step.input_from)
                step_params = {**step.params, "input": prev_result}
            else:
                step_params = step.params

            skill = self._get_skill(step.skill_name)
            if skill is None:
                if wf.on_error == "stop":
                    raise ValueError(f"Unknown skill: {step.skill_name}")
                elif wf.on_error == "skip":
                    continue
                continue

            try:
                result = skill(**step_params)
                self._cache_step_result(step.skill_name, result)
            except Exception as e:
                if wf.on_error == "stop":
                    raise
                elif wf.on_error == "retry":
                    for _ in range(3):
                        try:
                            result = skill(**step_params)
                            break
                        except Exception:
                            continue

        return result

    def _execute_parallel(self, wf: Workflow) -> list[Any]:
        """Execute steps concurrently."""
        futures = []
        for step in wf.steps:
            skill = self._get_skill(step.skill_name)
            if skill:
                future = self.executor.submit(skill, **step.params)
                futures.append((step.skill_name, future))
            elif wf.on_error == "stop":
                raise ValueError(f"Unknown skill: {step.skill_name}")

        results = []
        for name, future in futures:
            try:
                result = future.result(timeout=30)
                results.append({"skill": name, "result": result})
                self._cache_step_result(name, result)
            except Exception as e:
                if wf.on_error == "stop":
                    raise
                results.append({"skill": name, "error": str(e)})

        return results

    def _execute_branch(self, wf: Workflow) -> Any:
        """Execute one branch based on condition."""
        if not wf.condition:
            raise ValueError("BRANCH workflow requires a condition function")

        # Check each step as a potential branch
        for step in wf.steps:
            try:
                result = self._evaluate_condition(step.skill_name, wf.condition)
                if result:
                    skill = self._get_skill(step.skill_name)
                    if skill:
                        return skill(**step.params)
            except Exception:
                continue

        # Default: execute first step
        if wf.steps:
            step = wf.steps[0]
            skill = self._get_skill(step.skill_name)
            if skill:
                return skill(**step.params)

    def _execute_loop(self, wf: Workflow) -> Any:
        """Repeat until condition is met or max iterations reached."""
        result = None
        for i in range(wf.max_iterations):
            try:
                result = self._execute_sequence(wf)
                if wf.condition and wf.condition(result):
                    return result
            except Exception as e:
                if wf.on_error == "stop":
                    raise
                continue

        return result

    def _get_skill(self, name: str) -> Callable | None:
        """Get a skill from the registry."""
        return self._skill_registry.get(name)

    def _cache_step_result(self, step_name: str, result: Any) -> None:
        """Cache step results for inter-step communication."""
        if not hasattr(self, "_step_cache"):
            self._step_cache: dict[str, Any] = {}
        self._step_cache[step_name] = result

    def _get_step_result(self, step_name: str) -> Any:
        """Get cached result from a previous step."""
        return getattr(self, "_step_cache", {}).get(step_name)

    def _evaluate_condition(self, context: str, condition: Callable[[Any], bool]) -> bool:
        """Evaluate a condition function."""
        try:
            return condition(context)
        except Exception:
            return False

    @property
    def executor(self) -> concurrent.futures.ThreadPoolExecutor:
        return self._executor


# Workflow factory functions

def sequence_workflow(name: str, steps: list[tuple[str, dict]]) -> Workflow:
    """Create a SEQUENCE workflow."""
    return Workflow(
        name=name,
        operator=OperatorType.SEQUENCE,
        steps=[SkillStep(skill_name=s, params=p) for s, p in steps]
    )


def parallel_workflow(name: str, skills: list[tuple[str, dict]]) -> Workflow:
    """Create a PARALLEL workflow."""
    return Workflow(
        name=name,
        operator=OperatorType.PARALLEL,
        steps=[SkillStep(skill_name=s, params=p) for s, p in skills]
    )


def branch_workflow(name: str, branches: list[tuple[str, dict, Callable]],
                    default: tuple[str, dict]) -> Workflow:
    """Create a BRANCH workflow."""
    return Workflow(
        name=name,
        operator=OperatorType.BRANCH,
        steps=[SkillStep(skill_name=s, params=p) for s, p, _ in branches],
        condition=lambda ctx: any(
            cond(ctx) for _, _, cond in branches
        )
    )


def loop_workflow(name: str, steps: list[tuple[str, dict]],
                  until: Callable[[Any], bool], max_iter: int = 10) -> Workflow:
    """Create a LOOP workflow."""
    return Workflow(
        name=name,
        operator=OperatorType.LOOP,
        steps=[SkillStep(skill_name=s, params=p) for s, p in steps],
        condition=until,
        max_iterations=max_iter
    )
```

### 4.2 Example Compositions

```python
# Example: Evolution cycle as a composition
evolution_cycle_workflow = sequence_workflow("evolution_cycle", [
    ("memory_retrieve",     {"query": "recent_capability_gaps"}),
    ("reflector_analyze",   {"focus": "lowest_score"}),
    ("architect_design",    {"hypothesis": "from_reflector"}),
    ("reviewer_evaluate",   {"proposal": "from_architect"}),
    ("executor_apply",      {"approved": "from_reviewer"}),
    ("eval_run",            {"change_id": "from_executor"}),
    ("meta_learn_record",   {"outcome": "from_eval"}),
    ("memory_store",        {"insights": "all_above"}),
])

# Example: Parallel data fetch
research_workflow = parallel_workflow("web_research", [
    ("web_search",          {"query": "topic + latest news"}),
    ("web_search",          {"query": "topic + technical docs"}),
    ("web_search",          {"query": "topic + github repos"}),
])

# Example: Conditional execution
quality_check_workflow = branch_workflow("quality_gate", [
    ("publish_changes",  {"checks": "passed"},    lambda ctx: ctx == "passed"),
    ("fix_issues",      {"issues": "auto"},       lambda ctx: ctx == "failed"),
], default=("log_warning", {}))

# Example: Retry until success
api_retry_workflow = loop_workflow("robust_api_call", [
    ("api_call",         {"endpoint": "target"}),
    ("validate_result",  {}),
], until=lambda result: result and result.get("success"), max_iter=5)
```

---

## ═══════════════════════════════════════════════════════════════════════════════
## PART 5: META-LEARNING MODEL
## ═══════════════════════════════════════════════════════════════════════════════

```python
# meta_learning/meta_model.py
"""
Meta-Learning Model — tracks change-type success rates and optimizes strategy.
Hybrid approach: change-type priors from meta-learning + RL validation from eval.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from collections import defaultdict
import datetime


class MetaLearningModel:
    """
    Tracks what types of changes work for what types of capabilities.
    
    Success rate tracking per change type:
    - additive_code:      Adding new functions
    - semantic_tune:      Editing SKILL.md / prompts
    - refactor_existing:  Rewriting existing code
    - compositional:      Chaining skills together
    
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

    def __init__(self, boros_root: Path):
        self.boros_root = boros_root
        self.meta_file = boros_root / "session" / "meta_model.json"
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
            "weakest_patterns": [],
            "strongest_patterns": [],
            "blocked_change_types": [],
            "last_updated": ""
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
        score_delta: float
    ) -> None:
        """
        Record the outcome of a change.
        Updates success rates using exponential moving average.
        """
        if change_type not in self.CHANGE_TYPES:
            return

        # Update attempt count
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
                "total_regressions": 0
            }

        cap_hist = self.data["capability_history"][capability]
        cap_hist["last_change_type"] = change_type
        cap_hist["last_outcome"] = outcome
        if outcome == "improved":
            cap_hist["total_improvements"] += 1
        elif outcome == "regressed":
            cap_hist["total_regressions"] += 1

        # Update file history (for anti-brute-force)
        if target_file not in self.data["file_history"]:
            self.data["file_history"][target_file] = {
                "consecutive_failures": 0,
                "last_change_type": None,
                "last_outcome": None
            }

        file_hist = self.data["file_history"][target_file]
        if outcome == "regressed":
            file_hist["consecutive_failures"] += 1
            # Block if 2 consecutive failures
            if file_hist["consecutive_failures"] >= 2:
                if change_type not in self.data["blocked_change_types"]:
                    self.data["blocked_change_types"].append(change_type)
        else:
            file_hist["consecutive_failures"] = 0
            # Unblock if it worked
            if change_type in self.data["blocked_change_types"]:
                self.data["blocked_change_types"].remove(change_type)

        file_hist["last_change_type"] = change_type
        file_hist["last_outcome"] = outcome

        # Update patterns
        self._update_patterns()

        self._save()

    def suggest_change_type(self, capability: str) -> str:
        """
        Suggest the best change type for a capability.
        Based on historical success rates + capability-specific history.
        """
        # Check capability-specific history first
        cap_hist = self.data["capability_history"].get(capability, {})
        last_type = cap_hist.get("last_change_type")
        last_outcome = cap_hist.get("last_outcome")

        # If last change worked, try the same type
        if last_outcome == "improved" and last_type:
            return last_type

        # If last change failed, try a different type
        if last_outcome == "regressed" and last_type:
            alternatives = [ct for ct in self.CHANGE_TYPES if ct != last_type]
            if alternatives:
                # Pick best among alternatives
                return max(
                    alternatives,
                    key=lambda ct: self.data["change_type_success_rate"].get(ct, 0.0)
                )

        # Otherwise: pick highest-success-rate change type
        available = [
            ct for ct in self.CHANGE_TYPES
            if ct not in self.data["blocked_change_types"]
        ]

        if not available:
            return "additive_code"  # Safe fallback

        return max(
            available,
            key=lambda ct: self.data["change_type_success_rate"].get(ct, 0.0)
        )

    def should_block_file(self, target_file: str) -> tuple[bool, str]:
        """
        Check if a file should be blocked from changes.
        Anti-brute-force: 2+ consecutive failures = block.
        """
        file_hist = self.data["file_history"].get(target_file, {})
        failures = file_hist.get("consecutive_failures", 0)

        if failures >= 2:
            return True, f"File regressed {failures} consecutive times. Take a different approach."
        return False, ""

    def get_success_rate(self, change_type: str) -> float:
        """Get the success rate for a change type."""
        return self.data["change_type_success_rate"].get(change_type, 0.0)

    def get_all_rates(self) -> dict[str, float]:
        """Get all change type success rates."""
        return self.data["change_type_success_rate"].copy()

    def _update_patterns(self) -> None:
        """Update strongest and weakest patterns."""
        rates = self.data["change_type_success_rate"]
        attempts = self.data["change_type_attempts"]

        # Only consider types with enough data
        min_attempts = 3
        enough_data = {k: v for k, v in attempts.items() if v >= min_attempts}

        if not enough_data:
            return

        sorted_rates = sorted(enough_data.items(), key=lambda x: x[1])

        self.data["weakest_patterns"] = [k for k, _ in sorted_rates[:2]]
        self.data["strongest_patterns"] = [k for k, _ in sorted_rates[-2:]]


# RL Validation Layer (uses eval engine as reward signal)
class RLValidation:
    """
    RL-based validation: uses the eval engine as the environment,
    proposals as actions, score improvements as rewards.
    
    Currently uses the meta-learning model's success rates as policy.
    Can be upgraded to a neural policy network.
    """

    def __init__(self, meta_model: MetaLearningModel):
        self.meta_model = meta_model

    def evaluate_proposal(self, proposal: dict) -> dict:
        """
        Evaluate a change proposal using learned policy.
        Returns: {action: str, expected_reward: float, risk: float}
        """
        change_type = proposal.get("change_type", "")
        capability = proposal.get("capability", "")
        target_file = proposal.get("target_file", "")

        # Check if file is blocked
        blocked, reason = self.meta_model.should_block_file(target_file)
        if blocked:
            return {
                "action": "block",
                "reason": reason,
                "expected_reward": 0.0,
                "risk": 1.0
            }

        # Get success rate as expected reward
        success_rate = self.meta_model.get_success_rate(change_type)
        attempts = self.meta_model.data["change_type_attempts"].get(change_type, 0)

        # More attempts = more confidence in the rate
        confidence = min(1.0, attempts / 10.0)
        expected_reward = success_rate * confidence

        # Risk: low success rate + low attempts = high risk
        risk = (1.0 - success_rate) * (1.0 - confidence)

        action = "approve" if expected_reward > 0.2 else "review"

        return {
            "action": action,
            "expected_reward": expected_reward,
            "risk": risk,
            "confidence": confidence,
            "suggested_change_type": self.meta_model.suggest_change_type(capability)
        }

    def update_policy(self, proposal: dict, outcome: str, score_delta: float) -> None:
        """Update the policy based on outcome (called after eval)."""
        self.meta_model.record_outcome(
            change_type=proposal.get("change_type", ""),
            capability=proposal.get("capability", ""),
            target_file=proposal.get("target_file", ""),
            outcome=outcome,
            score_delta=score_delta
        )
```

---

## ═══════════════════════════════════════════════════════════════════════════════
## PART 6: METACOGNITION LAYER
## ═══════════════════════════════════════════════════════════════════════════════

```python
# metacognition/layer.py
"""
Metacognition Layer — self-monitoring, confidence calibration, loop detection.
The self-aware layer that watches Boros thinking about Boros.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Optional
from collections import Counter
import datetime


class MetacognitionLayer:
    """
    Self-monitoring layer for Boros.
    
    Responsibilities:
    1. Monitor reasoning traces for anomalies
    2. Calibrate confidence (know what you know)
    3. Detect reasoning loops
    4. Detect capability stagnation
    5. Self-modification (within safety bounds)
    """

    IMMOVABLE_COMPONENTS = {
        "world_model.terminal",
        "world_model.self_modification_bounds",
        "safety_layer",
        "metacognition.immovable",
    }

    def __init__(self, boros_root: Path):
        self.boros_root = boros_root
        self.state_file = boros_root / "session" / "metacognition.json"
        self.state = self._load()

        # Reasoning history for loop detection
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
            "self_modifications": []
        }

    def _save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2))

    def monitor_reasoning(self, reasoning_trace: list[str]) -> dict:
        """
        Monitor a reasoning trace for anomalies.
        Returns: {coherence: float, anomalies: list[str], loop: bool}
        """
        anomalies = []

        # Check coherence: reasoning steps should relate to each other
        coherence = self._check_coherence(reasoning_trace)

        # Detect anomalies
        if self._has_contradiction(reasoning_trace):
            anomalies.append("CONTRADICTION: reasoning steps contradict each other")
            self.state["anomalies_detected"] += 1

        if self._has_unfounded_claim(reasoning_trace):
            anomalies.append("UNFOUNDED_CLAIM: assertion without supporting evidence")

        if self._is_repeating_conclusions(reasoning_trace):
            anomalies.append("REPEATING_CONCLUSIONS: same conclusions reached repeatedly")

        # Check for loops
        loop_detected = self._detect_loop(reasoning_trace)
        if loop_detected:
            self.state["loop_count"] += 1
            anomalies.append(f"LOOP_DETECTED: reasoning is looping (count: {self.state['loop_count']})")

        # Update history
        self._reasoning_history = reasoning_trace[-20:]  # Keep last 20
        self.state["coherence_history"].append(coherence)
        if len(self.state["coherence_history"]) > 100:
            self.state["coherence_history"] = self.state["coherence_history"][-100:]

        self._save()

        return {
            "coherence": coherence,
            "anomalies": anomalies,
            "loop": loop_detected,
            "needs_attention": len(anomalies) > 0 or coherence < 0.5
        }

    def _check_coherence(self, trace: list[str]) -> float:
        """Check if reasoning steps form a coherent chain."""
        if len(trace) < 2:
            return 1.0

        # Simple heuristic: consecutive steps should have shared concepts
        shared_count = 0
        for i in range(len(trace) - 1):
            words_a = set(trace[i].lower().split())
            words_b = set(trace[i + 1].lower().split())
            shared = words_a & words_b
            if len(shared) >= 2:  # At least 2 shared words
                shared_count += 1

        return shared_count / max(1, len(trace) - 1)

    def _has_contradiction(self, trace: list[str]) -> bool:
        """Detect if reasoning contains contradictions."""
        positive = ["always", "definitely", "certainly", "proven", "confirmed"]
        negative = ["never", "impossible", "definitely not", "cannot"]

        pos_count = sum(1 for step in trace for w in positive if w in step.lower())
        neg_count = sum(1 for step in trace for w in negative if w in step.lower())

        return pos_count > 0 and neg_count > 0

    def _has_unfounded_claim(self, trace: list[str]) -> bool:
        """Detect claims without supporting evidence."""
        claim_indicators = ["should", "must", "will definitely", "obviously"]
        evidence_indicators = ["because", "evidence", "data", "shows", "tested", "proven"]

        for step in trace:
            has_claim = any(ind in step.lower() for ind in claim_indicators)
            has_evidence = any(ind in step.lower() for ind in evidence_indicators)
            if has_claim and not has_evidence and len(step) < 100:
                return True

        return False

    def _is_repeating_conclusions(self, trace: list[str]) -> bool:
        """Check if same conclusions are repeated."""
        conclusions = [s.strip()[-50:] for s in trace[-5:]]  # Last 50 chars
        return len(set(conclusions)) < len(conclusions) * 0.5

    def _detect_loop(self, trace: list[str]) -> bool:
        """Detect if reasoning is in a loop."""
        if len(trace) < 6:
            return False

        # Check for repeated patterns in the last N steps
        last_steps = trace[-6:]
        step_signatures = [s[:30].lower().strip() for s in last_steps]

        # If last 3 steps match last 3 steps of previous window, likely looping
        if len(self._last_reasoning) >= 6:
            prev_signatures = [s[:30].lower().strip() for s in self._last_reasoning[-6:]]
            if step_signatures == prev_signatures:
                return True

        self._last_reasoning = trace[-10:]
        return False

    def calibrate_confidence(self, prediction: str, actual_outcome: Any) -> dict:
        """
        Calibrate confidence: compare predicted confidence with actual outcome.
        Updates calibration error tracking.
        """
        # Get predicted confidence from state
        pred_conf = self.state["confidence_calibration"].get(prediction, {}).get(
            "predicted_confidence", 0.5
        )

        # Actual outcome: 0.0 to 1.0
        actual = 1.0 if actual_outcome else 0.0

        # Calibration error = |predicted - actual|
        error = abs(pred_conf - actual)

        # Update exponential moving average
        prev_entry = self.state["confidence_calibration"].get(prediction, {})
        prev_error = prev_entry.get("calibration_error", 0.5)
        new_error = 0.9 * prev_error + 0.1 * error

        self.state["confidence_calibration"][prediction] = {
            "predicted_confidence": pred_conf,
            "actual_outcome": actual,
            "calibration_error": new_error,
            "count": prev_entry.get("count", 0) + 1
        }

        self._save()

        return {
            "calibrated": new_error < 0.1,
            "calibration_error": new_error,
            "needs_retraining": new_error > 0.2
        }

    def detect_stagnation(self, capability: str, history: list[float]) -> dict:
        """
        Detect if improvement has stalled for a capability.
        Returns: {stalled: bool, since: int, suggestion: str}
        """
        if len(history) < 5:
            return {"stalled": False}

        recent = history[-5:]
        max_diff = max(recent) - min(recent)

        if max_diff < 0.01:
            return {
                "stalled": True,
                "since": len(history) - 5,
                "suggestion": f"Capability '{capability}' stalled. Try a different change type."
            }

        return {"stalled": False}

    def suggest_intervention(self) -> Optional[str]:
        """
        Suggest a metacognitive intervention based on current state.
        """
        # High loop count → break the loop
        if self.state["loop_count"] >= 3:
            self.state["loop_count"] = 0  # Reset counter
            self._save()
            return "LOOP_BREAK: Reset reasoning approach. Try a completely different strategy."

        # Low coherence → clarify thinking
        recent_coherence = self.state["coherence_history"][-10:]
        if recent_coherence and sum(recent_coherence) / len(recent_coherence) < 0.4:
            return "COHERENCE_LOW: Review reasoning chain. Ensure each step follows from the previous."

        # Many anomalies → pause and reconsider
        if self.state["anomalies_detected"] >= 5:
            self.state["anomalies_detected"] = 0
            self._save()
            return "ANOMALY_SUMMARY: Multiple anomalies detected. Pause and verify base assumptions."

        return None

    def self_modify(self, component: str, modification: dict) -> dict:
        """
        Attempt self-modification within safety bounds.
        Returns: {allowed: bool, reason: str}
        """
        # Check if component is immovable
        if component in self.IMMOVABLE_COMPONENTS:
            return {
                "allowed": False,
                "reason": f"Component '{component}' is in immovable set. Operator approval required."
            }

        # Log the modification
        self.state["self_modifications"].append({
            "component": component,
            "modification": modification,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        })

        self._save()
        return {"allowed": True, "reason": "Modification allowed within safety bounds"}
```

---

## ═══════════════════════════════════════════════════════════════════════════════
## PART 7: VERSION CONTROL
## ═══════════════════════════════════════════════════════════════════════════════

```python
# version_control/vc.py
"""
Full Git-Like Version Control for Boros.
Every change is recorded. Any state can be diffed and rolled back.
"""

from __future__ import annotations
import json
import shutil
import datetime
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Snapshot:
    id: str
    timestamp: str
    label: str
    cycle: int
    scores: dict
    changed_files: list[str]
    commit_message: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "label": self.label,
            "cycle": self.cycle,
            "scores": self.scores,
            "changed_files": self.changed_files,
            "commit_message": self.commit_message
        }


class VersionControl:
    """
    Full git-like version control for Boros.
    
    Features:
    - Snapshot every evolution cycle
    - Checkpoint before risky changes
    - Diff between any two snapshots
    - Rollback to any snapshot
    - Bisect to find which change broke something
    - Named versions (e.g., "pre-division-of-labor", "v1.2-stable")
    """

    def __init__(self, boros_root: Path):
        self.boros_root = boros_root
        self.snapshots_dir = boros_root / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        self.index_file = boros_root / "session" / "version_index.json"
        self.index = self._load_index()

        # Core files to track
        self.tracked_files = [
            "skills",
            "kernel.py",
            "agent_loop.py",
            "world_model.json",
            "manifest.json",
            "config.json",
        ]

    def _load_index(self) -> dict:
        if self.index_file.exists():
            return json.loads(self.index_file.read_text())
        return {"snapshots": [], "current": None, "branches": {}}

    def _save_index(self) -> None:
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        self.index_file.write_text(json.dumps(self.index, indent=2))

    def snapshot(self, label: str = "", cycle: int = 0,
                scores: dict = None, commit_message: str = "") -> str:
        """
        Create a full state snapshot.
        Returns snapshot ID.
        """
        import uuid
        snapshot_id = f"snap-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

        # Find changed files since last snapshot
        changed_files = self._find_changed_files()

        # Save snapshot metadata
        snap_meta = Snapshot(
            id=snapshot_id,
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            label=label or snapshot_id,
            cycle=cycle,
            scores=scores or {},
            changed_files=changed_files,
            commit_message=commit_message or f"Auto-snapshot: {label}"
        )

        # Save snapshot data
        snap_file = self.snapshots_dir / f"{snapshot_id}.json"
        snap_file.write_text(json.dumps(snap_meta.to_dict(), indent=2))

        # Copy current state of tracked files into snapshot
        snap_state_dir = self.snapshots_dir / snapshot_id
        snap_state_dir.mkdir(exist_ok=True)

        for rel_path in self.tracked_files:
            src = self.boros_root / rel_path
            dst = snap_state_dir / rel_path
            if src.exists():
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)

        # Update index
        self.index["snapshots"].append(snapshot_id)
        self.index["current"] = snapshot_id
        self._save_index()

        return snapshot_id

    def _find_changed_files(self) -> list[str]:
        """Find files that have changed since the last snapshot."""
        if not self.index["snapshots"]:
            return []

        last_snap = self.index["snapshots"][-1]
        last_snap_dir = self.snapshots_dir / last_snap

        changed = []
        for rel_path in self.tracked_files:
            src = self.boros_root / rel_path
            dst = last_snap_dir / rel_path

            if not src.exists():
                continue

            if src.is_dir():
                # Compare directories
                if not dst.exists():
                    changed.append(rel_path)
                elif not self._dirs_equal(src, dst):
                    changed.append(rel_path)
            else:
                # Compare files
                if not dst.exists() or src.read_bytes() != dst.read_bytes():
                    changed.append(rel_path)

        return changed

    def _dirs_equal(self, a: Path, b: Path) -> bool:
        """Check if two directories are equal."""
        import filecmp
        return filecmp.dircmp(a, b).left_only == []

    def diff(self, from_id: str, to_id: str) -> dict:
        """
        Show diff between two snapshots.
        Returns a dict with changed files and their diffs.
        """
        from_dir = self.snapshots_dir / from_id
        to_dir = self.snapshots_dir / to_id

        if not from_dir.exists() or not to_dir.exists():
            return {"error": "Snapshot not found"}

        diff_result = {}
        for rel_path in self.tracked_files:
            from_file = from_dir / rel_path
            to_file = to_dir / rel_path

            if not from_file.exists() and not to_file.exists():
                continue

            if not from_file.exists():
                diff_result[rel_path] = {"status": "added", "content": to_file.read_text()}
            elif not to_file.exists():
                diff_result[rel_path] = {"status": "deleted", "content": from_file.read_text()}
            else:
                # Compare
                import difflib
                from_lines = from_file.read_text().splitlines()
                to_lines = to_file.read_text().splitlines()
                diff = list(difflib.unified_diff(
                    from_lines, to_lines,
                    fromfile=str(from_file),
                    tofile=str(to_file),
                    lineterm=""
                ))
                if diff:
                    diff_result[rel_path] = {"status": "modified", "diff": "\n".join(diff)}

        return diff_result

    def rollback(self, snapshot_id: str) -> dict:
        """
        Rollback to a specific snapshot.
        Restores all tracked files to that snapshot's state.
        """
        snap_dir = self.snapshots_dir / snapshot_id
        if not snap_dir.exists():
            return {"error": f"Snapshot '{snapshot_id}' not found"}

        restored = []
        for rel_path in self.tracked_files:
            snap_file = snap_dir / rel_path
            dst = self.boros_root / rel_path

            if not snap_file.exists():
                continue

            if snap_file.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(snap_file, dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(snap_file, dst)

            restored.append(rel_path)

        # Mark as current
        self.index["current"] = snapshot_id
        self._save_index()

        return {"restored": restored, "snapshot": snapshot_id}

    def bisect(self, bad_id: str, good_id: str,
               test_func: callable) -> str:
        """
        Binary search through snapshots to find which change broke something.
        
        test_func: function that takes a snapshot_id and returns True if good, False if bad
        """
        snapshots = self.index["snapshots"]
        try:
            bad_idx = snapshots.index(bad_id)
            good_idx = snapshots.index(good_id)
        except ValueError:
            return "error: snapshot not found"

        if good_idx > bad_idx:
            good_idx, bad_idx = bad_idx, good_idx

        while good_idx < bad_idx - 1:
            mid_idx = (good_idx + bad_idx) // 2
            mid_id = snapshots[mid_idx]

            result = test_func(mid_id)
            if result:
                good_idx = mid_idx
            else:
                bad_idx = mid_idx

        return snapshots[bad_idx]

    def log(self, limit: int = 50) -> list[dict]:
        """Show recent snapshot history."""
        snapshots = []
        for snap_id in reversed(self.index["snapshots"][-limit:]):
            snap_file = self.snapshots_dir / f"{snap_id}.json"
            if snap_file.exists():
                snapshots.append(json.loads(snap_file.read_text()))
        return snapshots

    def tag(self, snapshot_id: str, tag_name: str) -> None:
        """Tag a snapshot with a name (e.g., "v1.0-stable")."""
        if "tags" not in self.index:
            self.index["tags"] = {}
        self.index["tags"][tag_name] = snapshot_id
        self._save_index()

    def get_tag(self, tag_name: str) -> Optional[str]:
        """Get snapshot ID for a tag."""
        return self.index.get("tags", {}).get(tag_name)
```

---

## ═══════════════════════════════════════════════════════════════════════════════
## PART 8: TUI v2 — CLEAN TERMINAL INTERFACE
## ═══════════════════════════════════════════════════════════════════════════════

### 8.1 Current Implementation (Final)

```
╭──────────────────────────────────────────────────────────────────────────────────────╮
│                                                                                      │
│                 ██████╗  ██████╗ ██████╗  ██████╗ ███████╗                          │
│                 ██╔══██╗██╔═══██╗██╔══██╗██╔═══██╗██╔════╝                          │
│                 ██████╔╝██║   ██║██████╔╝██║   ██║███████╗                          │
│                 ██╔══██╗██║   ██║██╔══██╗██║   ██║╚════██║                          │
│                 ██████╔╝╚██████╔╝██║  ██║╚██████╔╝███████║                          │
│                 ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝                          │
│                                                                                      │
│                 Self-Evolving Agent  ·  ARES                                       │
╰──────────────────────────────────────────────────────────────────────────────────────╯

  B.O.R.O.S  evolution  |  c3  |  gemini  |  16 skills

boros> 
```

### 8.2 Commands

```
s          status      — Current state (mode, cycle, generation, scores)
p          pause       — Pause after current cycle
r          resume      — Resume from pause
────────────────────────────────────────────────────────────────────
e          evolve      — Switch to evolution mode
w          work        — Switch to work mode
fork                    — Fork as deployment agent
rev                     — Re-evolve from fork
────────────────────────────────────────────────────────────────────
l [n]       logs        — Show last n log lines (default: 10)
sk          skills      — List all skills and function counts
sc          scores      — Show capability scores with bars
────────────────────────────────────────────────────────────────────
v           verbose    — Toggle verbose output
h           help       — Show this help
q           quit        — Exit
```

### 8.3 Files

**`start.py`** — Launch with logo, boot eval engine, show status line, hand off to interface

**`skills/director-interface/functions/interface.py`** — `DirectorInterface` class with:
- `boros>` prompt (pure `input()`, no prompt_toolkit)
- `_dispatch()` parses single-char commands
- Status line with mode | cycle | generation | paused
- Plain text output (no Rich tags)

---

## ═══════════════════════════════════════════════════════════════════════════════
## PART 9: FILE STRUCTURE
## ═══════════════════════════════════════════════════════════════════════════════

```
boros/
├── start.py                          # TUI launch
├── kernel.py                         # Core kernel
├── agent_loop.py                      # Main loop
├── tool_schemas.py                    # Tool definitions
├── world_model.json                   # Capability graph (v2)
│
├── adapters/                         # LLM providers
│   └── providers/
│       ├── gemini.py
│       ├── minimax.py
│       ├── anthropic.py
│       └── openai.py
│
├── agents/                           # Multi-agent system
│   ├── __init__.py
│   ├── messages.py                   # Agent message types
│   ├── bus.py                        # In-memory message bus
│   ├── reflector.py                 # Reflector agent
│   ├── architect.py                 # Architect agent
│   └── reviewer.py                  # Reviewer agent
│
├── eval_generator/                  # Eval sandbox
│   ├── eval_generator.py
│   ├── grpc_client.py               # gRPC client
│   ├── proto/                       # Protobuf definitions
│   │   ├── boros.proto
│   │   ├── eval_pb2.py
│   │   └── eval_pb2_grpc.py
│   └── shared/                       # File-based IPC (until gRPC)
│
├── skills/                           # Modular capabilities
│   ├── memory/
│   ├── reasoning/
│   ├── tool-use/
│   ├── reflection/
│   ├── meta-evolution/
│   ├── meta-evaluation/
│   ├── skill-forge/                  # Skill composition
│   │   ├── SKILL.md
│   │   └── composer.py              # Composition DSL
│   ├── eval-bridge/
│   ├── model-switcher/
│   └── director-interface/
│       └── functions/
│           └── interface.py         # TUI
│
├── meta_learning/                    # Meta-learning system
│   ├── __init__.py
│   └── meta_model.py                # Success rate tracking + RL
│
├── metacognition/                    # Self-monitoring
│   ├── __init__.py
│   └── layer.py                     # Reasoning monitor, loop detection
│
├── mcp/                              # MCP protocol layer
│   ├── __init__.py
│   └── protocol.py                  # Tools, resources, prompts
│
├── world_model/                      # World model engine
│   ├── __init__.py
│   └── capability_graph.py          # DAG of capabilities
│
├── version_control/                  # Git-like version control
│   ├── __init__.py
│   └── vc.py                        # Snapshots, diff, rollback, bisect
│
├── session/                          # Runtime state
│   ├── loop_state.json
│   ├── hypothesis.json
│   ├── meta_model.json
│   ├── metacognition.json
│   ├── version_index.json
│   └── lineage.json
│
├── memory/                           # RLM memory
│   └── sections/
│
├── snapshots/                        # Version control snapshots
│
├── logs/                             # Execution logs
│
├── tests/                            # Integration tests
│   ├── unit/
│   ├── integration/
│   │   ├── test_capability_graph.py
│   │   ├── test_meta_learning.py
│   │   ├── test_composition.py
│   │   └── test_version_control.py
│   └── e2e/
│
└── Dockerfile                        # Containerization
```

---

## ═══════════════════════════════════════════════════════════════════════════════
## PART 10: IMPLEMENTATION PHASES
## ═══════════════════════════════════════════════════════════════════════════════

### Phase 1: Core Stability (Week 1-2)
- [ ] Fix current TUI and UX flow ✅ DONE
- [ ] Ensure eval pipeline works reliably
- [ ] Add integration tests for capability graph
- [ ] Document current architecture

### Phase 2: Multi-Agent (Week 3-4)
- [ ] Create `agents/` directory with message bus
- [ ] Implement Reflector agent (read scores → hypotheses)
- [ ] Implement Architect agent (design proposals)
- [ ] Implement Reviewer agent (safety + quality gate)
- [ ] Wire agents into `agent_loop.py`

### Phase 3: gRPC + MCP (Week 5-6)
- [ ] Define `proto/boros.proto`
- [ ] Implement eval engine gRPC server
- [ ] Implement Boros gRPC client
- [ ] Replace file-polling eval bridge
- [ ] Implement MCP tools/resources/prompts

### Phase 4: World Model v2 (Week 7-8)
- [ ] Implement `world_model/capability_graph.py`
- [ ] Convert `world_model.json` to DAG format
- [ ] Implement prerequisite checking
- [ ] Implement emergent capability detection
- [ ] Dynamic capability discovery workflow

### Phase 5: Self-Monitoring (Week 9-10)
- [ ] Implement `metacognition/layer.py`
- [ ] Integrate with agent_loop for reasoning monitoring
- [ ] Implement confidence calibration
- [ ] Implement loop detection
- [ ] Implement stagnation detection

### Phase 6: Learning System (Week 11-12)
- [ ] Implement `meta_learning/meta_model.py`
- [ ] Track change-type success rates
- [ ] Implement anti-brute-force system
- [ ] Integrate RL validation
- [ ] Connect to agent_loop

### Phase 7: Version Control (Week 13-14)
- [ ] Implement `version_control/vc.py`
- [ ] Snapshot every evolution cycle
- [ ] Implement diff/rollback
- [ ] Implement bisect for regression finding
- [ ] Named tags

### Phase 8: Skill Composition (Week 15-16)
- [ ] Implement `skill-forge/composer.py`
- [ ] SEQUENCE/PARALLEL/BRANCH/LOOP operators
- [ ] Register skills with MCP
- [ ] Emergent capability detection from compositions

---

## ═══════════════════════════════════════════════════════════════════════════════
## PART 11: SAFETY & CONFIGURATION
## ═══════════════════════════════════════════════════════════════════════════════

### Immutable Components (Cannot be evolved)
```yaml
safety:
  immovable:
    - world_model.terminal           # AGI goal cannot change
    - world_model.self_modification_bounds  # Can't change what's changeable
    - metacognition.immovable       # Can't add to immovable list
    - kernel.unsafe_mode            # Cannot disable safety
  
  operator_only:                     # Requires explicit operator approval
    - world_model.structure          # Can't restructure the world model
    - safety.immutable               # Can't add to immovable list
    - version_control.enabled        # Can't disable version control
  
  auto_block:                        # Automatically blocked
    - file with 2+ consecutive failures  # Anti-brute-force
    - cosmetic-only changes          # Reviewer rejection
    - changes to eval-bridge         # Must preserve eval integrity
```

### Environment Variables
```bash
# Required
GEMINI_API_KEY=                    # Google Gemini API key

# Optional
ANTHROPIC_API_KEY=                 # Claude API (fallback)
MINIMAX_API_KEY=                   # MiniMax API (fallback)
OPENAI_API_KEY=                    # GPT API (fallback)

# Configuration
BOROS_MODE=evolution               # evolution | employee
BOROS_LLM=gemini                   # Default provider
BOROS_EVAL_HOST=localhost          # gRPC eval engine host
BOROS_EVAL_PORT=50051              # gRPC eval engine port
```

---

## ═══════════════════════════════════════════════════════════════════════════════
## APPENDIX: DECISION SUMMARY TABLE
## ═══════════════════════════════════════════════════════════════════════════════

| # | Question | Answer | Rationale |
|---|----------|--------|-----------|
| Q1 | Terminal Purpose | **A: General AGI** | Harness masters any world model |
| Q2 | Success Criteria | **E: Both** | Autonomous improvement + quality |
| Q3 | Safety Model | **D: Goal lock** | World model terminal goals immutable |
| Q4 | Agent Architecture | **B: 2-3 agents** | Scalable, reduces bias |
| Q5 | Protocol | **D: gRPC + MCP** | Real-time, industry standard |
| Q6 | World Model | **Redesign** | Capability graph, not flat |
| Q7 | Self-Monitoring | **D: Self-modifying** | Full metacognition |
| Q8 | Learning | **Hybrid** | Meta-learning + RL validation |
| Q9 | Version Control | **B: Full git** | Complete history, rollback |
| Q10 | Composition | **C: Operators** | SEQUENCE, PARALLEL, BRANCH, LOOP |
| Q11 | Deployment | **A: Single → Docker** | Scale as needed |
| Q12 | Testing | **B: Integration** | Real-world validation |
| Q13 | Observability | **C: Full APM** | Everything measured |

---

**END OF BLUEPRINT v2.0**

*This document is the complete, executable architecture plan.
Each component has real implementation code that can be built immediately.*