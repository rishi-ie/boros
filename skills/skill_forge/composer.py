"""
Skill Composition DSL — operators: SEQUENCE, PARALLEL, BRANCH, LOOP.
Enables emergent capabilities through skill chaining.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
import concurrent.futures


class OperatorType(Enum):
    SEQUENCE = "sequence"
    PARALLEL = "parallel"
    BRANCH = "branch"
    LOOP = "loop"


@dataclass
class SkillStep:
    skill_name: str
    params: dict = field(default_factory=dict)
    input_from: str | None = None  # Which step's output to use as input


@dataclass
class Workflow:
    name: str
    operator: OperatorType
    steps: list[SkillStep] = field(default_factory=list)
    condition: Callable[[Any], bool] | None = None
    max_iterations: int = 10
    on_error: str = "stop"  # "stop", "skip", "retry"


# ── Workflow Factory ──────────────────────────────────────────────────────────

def sequence_workflow(
    name: str, steps: list[tuple[str, dict]]
) -> Workflow:
    """Create a SEQUENCE workflow."""
    return Workflow(
        name=name,
        operator=OperatorType.SEQUENCE,
        steps=[SkillStep(skill_name=s, params=p) for s, p in steps],
    )


def parallel_workflow(
    name: str, skills: list[tuple[str, dict]]
) -> Workflow:
    """Create a PARALLEL workflow."""
    return Workflow(
        name=name,
        operator=OperatorType.PARALLEL,
        steps=[SkillStep(skill_name=s, params=p) for s, p in skills],
    )


def loop_workflow(
    name: str,
    steps: list[tuple[str, dict]],
    until: Callable[[Any], bool],
    max_iter: int = 10,
) -> Workflow:
    """Create a LOOP workflow."""
    return Workflow(
        name=name,
        operator=OperatorType.LOOP,
        steps=[SkillStep(skill_name=s, params=p) for s, p in steps],
        condition=until,
        max_iterations=max_iter,
    )


# ── Skill Composer ─────────────────────────────────────────────────────────────

class SkillComposer:
    """
    Composes skills into workflows using operators.

    Example:
      composer = SkillComposer(kernel)
      composer.register_skill("read", read_handler)
      composer.register_skill("analyze", analyze_handler)

      workflow = sequence_workflow("analyze_and_read", [
          ("read", {"path": "/data"}),
          ("analyze", {}),
      ])
      result = composer.execute(workflow)
    """

    def __init__(self, kernel):
        self.kernel = kernel
        self._skill_registry: dict[str, Callable] = {}
        self._step_cache: dict[str, Any] = {}
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)

    def register_skill(self, name: str, handler: Callable) -> None:
        """Register a skill that can be used in compositions."""
        self._skill_registry[name] = handler

    def execute(self, workflow: Workflow) -> Any:
        """Execute a composed workflow. Returns the final result."""
        self._step_cache.clear()

        if workflow.operator == OperatorType.SEQUENCE:
            return self._execute_sequence(workflow)
        elif workflow.operator == OperatorType.PARALLEL:
            return self._execute_parallel(workflow)
        elif workflow.operator == OperatorType.BRANCH:
            return self._execute_branch(workflow)
        elif workflow.operator == OperatorType.LOOP:
            return self._execute_loop(workflow)

    def _get_skill(self, name: str) -> Callable | None:
        return self._skill_registry.get(name)

    def _cache(self, name: str, result: Any) -> None:
        self._step_cache[name] = result

    def _input_from(self, input_from: str | None) -> Any:
        if input_from is None:
            return None
        return self._step_cache.get(input_from)

    def _execute_sequence(self, wf: Workflow) -> Any:
        result = None
        for step in wf.steps:
            skill = self._get_skill(step.skill_name)
            if skill is None:
                if wf.on_error == "stop":
                    raise ValueError(f"Unknown skill: {step.skill_name}")
                continue

            params = dict(step.params)
            inp = self._input_from(step.input_from)
            if inp is not None:
                params["_input"] = inp

            try:
                result = skill(**params)
                self._cache(step.skill_name, result)
            except Exception as e:
                if wf.on_error == "stop":
                    raise
                elif wf.on_error == "skip":
                    continue
        return result

    def _execute_parallel(self, wf: Workflow) -> list[dict]:
        futures = []
        for step in wf.steps:
            skill = self._get_skill(step.skill_name)
            if skill:
                future = self._executor.submit(skill, **step.params)
                futures.append((step.skill_name, future))

        results = []
        for name, future in futures:
            try:
                result = future.result(timeout=30)
                self._cache(name, result)
                results.append({"skill": name, "result": result, "success": True})
            except Exception as e:
                results.append({"skill": name, "error": str(e), "success": False})
        return results

    def _execute_branch(self, wf: Workflow) -> Any:
        """Execute first step with condition=True, or first step as fallback."""
        for step in wf.steps:
            if wf.condition and wf.condition(step.skill_name):
                skill = self._get_skill(step.skill_name)
                if skill:
                    return skill(**step.params)

        # Default: first step
        if wf.steps:
            step = wf.steps[0]
            skill = self._get_skill(step.skill_name)
            if skill:
                return skill(**step.params)

    def _execute_loop(self, wf: Workflow) -> Any:
        result = None
        for i in range(wf.max_iterations):
            try:
                result = self._execute_sequence(wf)
                if wf.condition and wf.condition(result):
                    return result
            except Exception as e:
                if wf.on_error == "stop":
                    raise
        return result

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)