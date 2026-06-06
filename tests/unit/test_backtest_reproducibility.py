"""Unit tests for backtest experiment reproducibility tracking."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from stat_arb.backtest import (
    BacktestCostConfig,
    BaselineAsset,
    BaselineSide,
    BuyAndHoldBaselineConfig,
    CostAssumptionStatus,
    CostSensitivityScenario,
    PerformanceMetricConfig,
    calculate_config_hash,
    create_reproducibility_manifest,
    hash_file,
)

TASKS_PATH = Path(".kiro/specs/quant-research-architecture/tasks.md")
REPRODUCIBILITY_PATH = Path("src/stat_arb/backtest/reproducibility.py")
DECISIONS_BACKTESTING_PATH = Path("docs/knowledge/decisions_backtesting.md")


def test_reproducibility_manifest_records_required_metadata(tmp_path: Path) -> None:
    """Manifest should record code, config, datasets, seed, command, timestamp, and lock hash."""
    lock_file = tmp_path / "uv.lock"
    lock_file.write_text("package-a==1.0\n", encoding="utf-8")
    timestamp = datetime(2026, 6, 6, 12, 0, tzinfo=UTC)

    manifest = create_reproducibility_manifest(
        git_commit_hash="ABCDEF1",
        config_components=_config_components(),
        dataset_ids=("dataset-a", "dataset-b"),
        random_seed=123,
        execution_command=("stat-arb", "backtest", "--config", "experiment.yml"),
        run_timestamp=timestamp,
        lock_file_path=lock_file,
    )

    assert manifest.git_commit_hash == "abcdef1"
    assert len(manifest.config_hash) == 64
    assert manifest.dataset_ids == ("dataset-a", "dataset-b")
    assert manifest.random_seed == 123
    assert manifest.execution_command == ("stat-arb", "backtest", "--config", "experiment.yml")
    assert manifest.run_timestamp == timestamp
    assert manifest.lock_file_hash == hash_file(lock_file)


def test_config_hash_is_stable_and_covers_research_assumptions() -> None:
    """Baseline, metrics, costs, and sensitivity scenarios must be part of config hash."""
    base = _config_components()
    reordered = {
        "sensitivity_scenarios": base["sensitivity_scenarios"],
        "metric_config": base["metric_config"],
        "baseline_config": base["baseline_config"],
        "cost_config": base["cost_config"],
    }
    changed_baseline = {
        **base,
        "baseline_config": BuyAndHoldBaselineConfig(
            name="long_asset_a_two_units",
            asset=BaselineAsset.ASSET_A,
            side=BaselineSide.LONG,
            units=2.0,
            initial_capital=100.0,
        ),
    }
    changed_metric = {
        **base,
        "metric_config": PerformanceMetricConfig(
            periods_per_year=365,
            risk_free_rate_per_period=0.0001,
            var_confidence=0.95,
            cvar_confidence=0.95,
        ),
    }
    changed_cost = {
        **base,
        "cost_config": BacktestCostConfig(
            commission_rate=0.002,
            spread_cost_rate=0.0005,
            slippage_rate=0.0002,
            funding_rate_daily=0.0001,
            borrow_rate_annual=0.005,
            status=CostAssumptionStatus.VERIFIED,
            source="unit-test",
            verified_at=datetime(2026, 6, 6, tzinfo=UTC),
            venue="test-exchange",
            market_type="perpetual",
        ),
    }
    changed_sensitivity = {
        **base,
        "sensitivity_scenarios": (
            CostSensitivityScenario(name="triple_costs", cost_multiplier=3.0),
        ),
    }

    base_hash = calculate_config_hash(base)
    assert calculate_config_hash(reordered) == base_hash
    assert calculate_config_hash(changed_baseline) != base_hash
    assert calculate_config_hash(changed_metric) != base_hash
    assert calculate_config_hash(changed_cost) != base_hash
    assert calculate_config_hash(changed_sensitivity) != base_hash


def test_reproducibility_manifest_validates_inputs(tmp_path: Path) -> None:
    """Invalid reproducibility metadata should fail before registry persistence."""
    lock_file = tmp_path / "uv.lock"
    lock_file.write_text("lock", encoding="utf-8")
    kwargs = {
        "git_commit_hash": "abcdef1",
        "config_components": _config_components(),
        "dataset_ids": ("dataset-a",),
        "random_seed": None,
        "execution_command": ("stat-arb", "backtest"),
        "run_timestamp": datetime(2026, 6, 6, tzinfo=UTC),
        "lock_file_path": lock_file,
    }

    with pytest.raises(ValueError, match="git_commit_hash"):
        create_reproducibility_manifest(**{**kwargs, "git_commit_hash": "not-a-hash"})
    with pytest.raises(ValueError, match="dataset_ids"):
        create_reproducibility_manifest(**{**kwargs, "dataset_ids": ("same", "same")})
    with pytest.raises(TypeError, match="random_seed"):
        create_reproducibility_manifest(**{**kwargs, "random_seed": True})
    with pytest.raises(ValueError, match="execution_command"):
        create_reproducibility_manifest(**{**kwargs, "execution_command": ()})
    with pytest.raises(ValueError, match="timezone-aware"):
        create_reproducibility_manifest(
            **{**kwargs, "run_timestamp": datetime(2026, 6, 6)}
        )
    with pytest.raises(FileNotFoundError):
        create_reproducibility_manifest(**{**kwargs, "lock_file_path": tmp_path / "missing.lock"})


def test_reproducibility_task_is_closed_with_no_partial_config_hash() -> None:
    """Task 7.10 should be closed and config hash should cover all research assumptions."""
    tasks = TASKS_PATH.read_text(encoding="utf-8")
    implementation = REPRODUCIBILITY_PATH.read_text(encoding="utf-8")
    decisions = DECISIONS_BACKTESTING_PATH.read_text(encoding="utf-8")

    assert "- [x] 7.10 Implement experiment reproducibility tracking" in tasks
    assert "DEC-0046" in decisions
    assert "baseline" not in implementation.lower()
    assert "config_components" in implementation


def _config_components() -> dict[str, object]:
    return {
        "baseline_config": BuyAndHoldBaselineConfig(
            name="long_asset_a_one_unit",
            asset=BaselineAsset.ASSET_A,
            side=BaselineSide.LONG,
            units=1.0,
            initial_capital=100.0,
        ),
        "metric_config": PerformanceMetricConfig(
            periods_per_year=365,
            risk_free_rate_per_period=0.0,
            var_confidence=0.95,
            cvar_confidence=0.95,
        ),
        "cost_config": BacktestCostConfig(
            commission_rate=0.001,
            spread_cost_rate=0.0005,
            slippage_rate=0.0002,
            funding_rate_daily=0.0001,
            borrow_rate_annual=0.005,
            status=CostAssumptionStatus.VERIFIED,
            source="unit-test",
            verified_at=datetime(2026, 6, 6, tzinfo=UTC),
            venue="test-exchange",
            market_type="perpetual",
        ),
        "sensitivity_scenarios": (
            CostSensitivityScenario(name="double_costs", cost_multiplier=2.0),
            CostSensitivityScenario(name="half_costs", cost_multiplier=0.5),
        ),
    }
