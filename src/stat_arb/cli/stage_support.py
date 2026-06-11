"""Explicit support policy for local experiment stage execution."""

from __future__ import annotations

from dataclasses import dataclass

from stat_arb.agents import ExperimentLifecycleStatus


@dataclass(frozen=True)
class StageExecutionSpec:
    """Task queue contract required to execute one supported stage."""

    task_type: str
    agent_name: str


_SUPPORTED_EXECUTE_STAGE_SPECS: dict[ExperimentLifecycleStatus, StageExecutionSpec] = {
    ExperimentLifecycleStatus.STATISTICAL_TESTING: StageExecutionSpec(
        task_type="run_statistical_tests",
        agent_name="statistical_testing_agent",
    ),
    ExperimentLifecycleStatus.BACKTESTING: StageExecutionSpec(
        task_type="run_backtest",
        agent_name="backtest_agent",
    ),
    ExperimentLifecycleStatus.CRITIC_REVIEW: StageExecutionSpec(
        task_type="run_critic_review",
        agent_name="critic_agent",
    ),
}


_BLOCKED_EXECUTE_STAGE_REASONS: dict[ExperimentLifecycleStatus, str] = {
    ExperimentLifecycleStatus.DATA_VALIDATION: (
        "Data Agent service boundary is not yet implemented for execute-stage."
    ),
    ExperimentLifecycleStatus.REPORTING: (
        "Reporting requires factual artifact/series sidecars before CLI execution."
    ),
    ExperimentLifecycleStatus.FINAL_DECISION: (
        "final decision is Coordinator-owned and must use the final-decision boundary."
    ),
    ExperimentLifecycleStatus.NEW: "new is a lifecycle status, not an executable stage.",
}


def supported_execute_stages() -> tuple[ExperimentLifecycleStatus, ...]:
    """Return stages currently safe to execute from the CLI."""
    return tuple(_SUPPORTED_EXECUTE_STAGE_SPECS)


def execute_stage_spec(stage: ExperimentLifecycleStatus) -> StageExecutionSpec:
    """Return the explicit task contract for a supported executable stage."""
    spec = _SUPPORTED_EXECUTE_STAGE_SPECS.get(stage)
    if spec is None:
        reason = blocked_execute_stage_reason(stage)
        raise ValueError(f"execute-stage не поддерживает stage {stage.value}: {reason}")
    return spec


def blocked_execute_stage_reason(stage: ExperimentLifecycleStatus) -> str:
    """Return the architectural reason why a stage is not executable yet."""
    return _BLOCKED_EXECUTE_STAGE_REASONS.get(
        stage,
        "stage is not registered as a mature CLI execution boundary.",
    )
