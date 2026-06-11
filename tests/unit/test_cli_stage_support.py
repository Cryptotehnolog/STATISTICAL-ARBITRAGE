"""Unit tests for explicit CLI stage execution support policy."""

from __future__ import annotations

import pytest

from stat_arb.agents import ExperimentLifecycleStatus
from stat_arb.cli.stage_support import (
    StageExecutionSpec,
    blocked_execute_stage_reason,
    execute_stage_spec,
    supported_execute_stages,
)


def test_supported_execute_stages_are_mature_agent_boundaries_only() -> None:
    """execute-stage should expose only stages with mature service boundaries."""
    assert supported_execute_stages() == (
        ExperimentLifecycleStatus.STATISTICAL_TESTING,
        ExperimentLifecycleStatus.BACKTESTING,
        ExperimentLifecycleStatus.CRITIC_REVIEW,
    )


def test_execute_stage_spec_maps_task_type_and_agent_explicitly() -> None:
    """Each supported stage should have an explicit task type and agent name."""
    assert execute_stage_spec(
        ExperimentLifecycleStatus.STATISTICAL_TESTING
    ) == StageExecutionSpec(
        task_type="run_statistical_tests",
        agent_name="statistical_testing_agent",
    )
    assert execute_stage_spec(ExperimentLifecycleStatus.BACKTESTING) == StageExecutionSpec(
        task_type="run_backtest",
        agent_name="backtest_agent",
    )
    assert execute_stage_spec(ExperimentLifecycleStatus.CRITIC_REVIEW) == StageExecutionSpec(
        task_type="run_critic_review",
        agent_name="critic_agent",
    )


def test_blocked_execute_stages_have_human_readable_reasons() -> None:
    """Unsupported stages should fail closed with durable architectural reasons."""
    assert "Data Agent service boundary" in blocked_execute_stage_reason(
        ExperimentLifecycleStatus.DATA_VALIDATION
    )
    assert "factual artifact/series sidecars" in blocked_execute_stage_reason(
        ExperimentLifecycleStatus.REPORTING
    )
    assert "final decision is Coordinator-owned" in blocked_execute_stage_reason(
        ExperimentLifecycleStatus.FINAL_DECISION
    )


def test_execute_stage_spec_rejects_unsupported_stages() -> None:
    """Unsupported stages should not silently receive an inferred task mapping."""
    with pytest.raises(ValueError, match="execute-stage не поддерживает stage reporting"):
        execute_stage_spec(ExperimentLifecycleStatus.REPORTING)
