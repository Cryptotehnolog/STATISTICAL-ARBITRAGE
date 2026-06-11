"""Typed builders for experiment stage JSON payloads."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from stat_arb.agents import BacktestAgentInput, StatisticalTestingInput
from stat_arb.backtest import (
    BacktestCostConfig,
    BacktestExitPolicyConfig,
    BaselineAsset,
    BaselineSide,
    BuyAndHoldBaselineConfig,
    CostAssumptionStatus,
    CostSensitivityScenario,
    PerformanceMetricConfig,
    calculate_performance_metrics,
    compare_to_buy_and_hold_baseline,
    create_reproducibility_manifest,
    run_cost_sensitivity_analysis,
    run_pair_backtest_core,
)


def build_statistical_testing_input(payload: dict[str, object]) -> StatisticalTestingInput:
    """Build a Statistical Testing Agent input from an explicit stage payload."""
    return StatisticalTestingInput(
        hypothesis_id=_payload_uuid(payload, "hypothesis_id"),
        dataset_a_id=_payload_uuid(payload, "dataset_a_id"),
        dataset_b_id=_payload_uuid(payload, "dataset_b_id"),
        prices_a=_payload_float_list(payload, "prices_a"),
        prices_b=_payload_float_list(payload, "prices_b"),
        aligned_timestamps=_payload_datetimes(payload, "aligned_timestamps"),
        train_fraction=_payload_float(payload, "train_fraction"),
        alpha=_payload_float(payload, "alpha"),
        adf_regression=_payload_string(payload, "adf_regression"),
        adf_autolag=_payload_optional_string(payload, "adf_autolag"),
        periods_per_day=_payload_float(payload, "periods_per_day"),
        residual_diagnostics_lags=_payload_int(payload, "residual_diagnostics_lags"),
        regime_window=_payload_int(payload, "regime_window"),
        regime_mean_shift_threshold=_payload_float(
            payload,
            "regime_mean_shift_threshold",
        ),
        regime_volatility_ratio_threshold=_payload_float(
            payload,
            "regime_volatility_ratio_threshold",
        ),
    )


def build_backtest_agent_input(payload: dict[str, object]) -> BacktestAgentInput:
    """Build a Backtest Agent persistence input from an explicit stage payload."""
    prices_a = _payload_float_list(payload, "prices_a")
    prices_b = _payload_float_list(payload, "prices_b")
    aligned_timestamps = _payload_datetimes(payload, "aligned_timestamps")
    z_scores = _payload_float_list(payload, "z_scores")
    core = run_pair_backtest_core(
        prices_a=prices_a,
        prices_b=prices_b,
        z_scores=z_scores,
        aligned_timestamps=aligned_timestamps,
        hedge_ratio=_payload_float(payload, "hedge_ratio"),
        entry_threshold=_payload_float(payload, "entry_threshold"),
        exit_threshold=_payload_float(payload, "exit_threshold"),
        exit_policy=_payload_exit_policy(payload),
        risk_exit_policy_disabled_reason=_payload_optional_string(
            payload,
            "risk_exit_policy_disabled_reason",
        ),
    )
    cost_config = _payload_cost_config(_payload_object(payload, "cost_config"))
    periods_per_day = _payload_float(payload, "periods_per_day")
    average_portfolio_value = _payload_optional_float(payload, "average_portfolio_value")
    sensitivity_scenarios = tuple(
        CostSensitivityScenario(
            name=_object_string(item, "name", context="payload.sensitivity_scenarios[]"),
            cost_multiplier=_object_float(
                item,
                "cost_multiplier",
                context="payload.sensitivity_scenarios[]",
            ),
        )
        for item in _payload_object_list(payload, "sensitivity_scenarios")
    )
    sensitivity = run_cost_sensitivity_analysis(
        core,
        base_cost_config=cost_config,
        periods_per_day=periods_per_day,
        average_portfolio_value=average_portfolio_value,
        scenarios=sensitivity_scenarios,
    )
    metric_config = _payload_metric_config(_payload_object(payload, "metric_config"))
    period_returns = _payload_float_list(payload, "period_returns")
    baseline_config = _payload_buy_and_hold_baseline_config(
        _payload_object(payload, "baseline_config")
    )
    metrics = calculate_performance_metrics(
        equity_curve=_payload_float_list(payload, "equity_curve"),
        period_returns=period_returns,
        trade_pnls=_payload_float_list(payload, "trade_pnls"),
        core_result=core,
        config=metric_config,
    )
    baseline = compare_to_buy_and_hold_baseline(
        strategy_period_returns=period_returns,
        prices_a=prices_a,
        prices_b=prices_b,
        aligned_timestamps=aligned_timestamps,
        baseline_config=baseline_config,
        metric_config=metric_config,
    )
    reproducibility_payload = _payload_object(payload, "reproducibility")
    reproducibility = create_reproducibility_manifest(
        git_commit_hash=_object_string(
            reproducibility_payload,
            "git_commit_hash",
            context="payload.reproducibility",
        ),
        config_components={
            "core": {
                "hedge_ratio": core.hedge_ratio,
                "entry_threshold": core.entry_threshold,
                "exit_threshold": core.exit_threshold,
                "exit_policy": core.exit_policy,
                "risk_exit_policy_disabled_reason": core.risk_exit_policy_disabled_reason,
            },
            "cost_config": cost_config,
            "metric_config": metric_config,
            "baseline_config": baseline_config,
            "sensitivity_scenarios": sensitivity_scenarios,
        },
        dataset_ids=_object_string_list(
            reproducibility_payload,
            "dataset_ids",
            context="payload.reproducibility",
        ),
        random_seed=_object_optional_int(
            reproducibility_payload,
            "random_seed",
            context="payload.reproducibility",
        ),
        execution_command=_object_string_list(
            reproducibility_payload,
            "execution_command",
            context="payload.reproducibility",
        ),
        run_timestamp=_object_datetime(
            reproducibility_payload,
            "run_timestamp",
            context="payload.reproducibility",
        ),
        lock_file_path=_object_string(
            reproducibility_payload,
            "lock_file_path",
            context="payload.reproducibility",
        ),
    )
    return BacktestAgentInput(
        hypothesis_id=_payload_uuid(payload, "hypothesis_id"),
        test_id=_payload_uuid(payload, "test_id"),
        dataset_a_id=_payload_uuid(payload, "dataset_a_id"),
        dataset_b_id=_payload_uuid(payload, "dataset_b_id"),
        core_result=core,
        pnl=sensitivity.base,
        metrics=metrics,
        baseline=baseline,
        sensitivity=sensitivity,
        reproducibility=reproducibility,
        train_window_days=_payload_int(payload, "train_window_days"),
        test_window_days=_payload_int(payload, "test_window_days"),
        num_windows=_payload_int(payload, "num_windows"),
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            "ожидается ISO datetime, например 2024-01-01T00:00:00+00:00"
        ) from exc


def _payload_uuid(payload: dict[str, object], key: str) -> UUID:
    return UUID(_payload_string(payload, key))


def _payload_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"payload.{key} must be a non-empty string")
    return value


def _payload_optional_string(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"payload.{key} must be a string or null")
    return value


def _payload_float(payload: dict[str, object], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"payload.{key} must be a number")
    return float(value)


def _payload_optional_float(payload: dict[str, object], key: str) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"payload.{key} must be a number or null")
    return float(value)


def _payload_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"payload.{key} must be an integer")
    return value


def _payload_object(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"payload.{key} must be an object")
    return value


def _payload_object_list(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"payload.{key} must be a list of objects")
    return value


def _payload_float_list(payload: dict[str, object], key: str) -> list[float]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"payload.{key} must be a list")
    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int | float):
            raise ValueError(f"payload.{key} must contain only numbers")
        result.append(float(item))
    return result


def _payload_exit_policy(payload: dict[str, object]) -> BacktestExitPolicyConfig | None:
    value = payload.get("exit_policy")
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("payload.exit_policy must be an object or null")
    return BacktestExitPolicyConfig(
        max_holding_bars=_object_optional_int(
            value,
            "max_holding_bars",
            context="payload.exit_policy",
        ),
        emergency_z_score=_object_optional_float(
            value,
            "emergency_z_score",
            context="payload.exit_policy",
        ),
    )


def _payload_cost_config(value: dict[str, object]) -> BacktestCostConfig:
    return BacktestCostConfig(
        commission_rate=_object_float(value, "commission_rate", context="payload.cost_config"),
        spread_cost_rate=_object_float(value, "spread_cost_rate", context="payload.cost_config"),
        slippage_rate=_object_float(value, "slippage_rate", context="payload.cost_config"),
        funding_rate_daily=_object_float(
            value,
            "funding_rate_daily",
            context="payload.cost_config",
        ),
        borrow_rate_annual=_object_float(
            value,
            "borrow_rate_annual",
            context="payload.cost_config",
        ),
        status=CostAssumptionStatus(
            _object_string(value, "status", context="payload.cost_config")
        ),
        source=_object_string(value, "source", context="payload.cost_config"),
        verified_at=_object_datetime(value, "verified_at", context="payload.cost_config"),
        venue=_object_string(value, "venue", context="payload.cost_config"),
        market_type=_object_string(value, "market_type", context="payload.cost_config"),
        notes=_object_optional_string(value, "notes", context="payload.cost_config") or "",
    )


def _payload_metric_config(value: dict[str, object]) -> PerformanceMetricConfig:
    return PerformanceMetricConfig(
        periods_per_year=_object_int(value, "periods_per_year", context="payload.metric_config"),
        risk_free_rate_per_period=_object_float(
            value,
            "risk_free_rate_per_period",
            context="payload.metric_config",
        ),
        var_confidence=_object_float(value, "var_confidence", context="payload.metric_config"),
        cvar_confidence=_object_float(value, "cvar_confidence", context="payload.metric_config"),
    )


def _payload_buy_and_hold_baseline_config(
    value: dict[str, object],
) -> BuyAndHoldBaselineConfig:
    kind = _object_string(value, "kind", context="payload.baseline_config")
    if kind != "buy_and_hold":
        raise ValueError("payload.baseline_config.kind must be buy_and_hold")
    return BuyAndHoldBaselineConfig(
        name=_object_string(value, "name", context="payload.baseline_config"),
        asset=BaselineAsset(_object_string(value, "asset", context="payload.baseline_config")),
        side=BaselineSide(_object_string(value, "side", context="payload.baseline_config")),
        units=_object_float(value, "units", context="payload.baseline_config"),
        initial_capital=_object_float(
            value,
            "initial_capital",
            context="payload.baseline_config",
        ),
    )


def _object_string(value: dict[str, object], key: str, *, context: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"{context}.{key} must be a non-empty string")
    return item


def _object_optional_string(
    value: dict[str, object],
    key: str,
    *,
    context: str,
) -> str | None:
    item = value.get(key)
    if item is None:
        return None
    if not isinstance(item, str):
        raise ValueError(f"{context}.{key} must be a string or null")
    return item


def _object_float(value: dict[str, object], key: str, *, context: str) -> float:
    item = value.get(key)
    if isinstance(item, bool) or not isinstance(item, int | float):
        raise ValueError(f"{context}.{key} must be a number")
    return float(item)


def _object_optional_float(
    value: dict[str, object],
    key: str,
    *,
    context: str,
) -> float | None:
    item = value.get(key)
    if item is None:
        return None
    if isinstance(item, bool) or not isinstance(item, int | float):
        raise ValueError(f"{context}.{key} must be a number or null")
    return float(item)


def _object_int(value: dict[str, object], key: str, *, context: str) -> int:
    item = value.get(key)
    if isinstance(item, bool) or not isinstance(item, int):
        raise ValueError(f"{context}.{key} must be an integer")
    return item


def _object_optional_int(
    value: dict[str, object],
    key: str,
    *,
    context: str,
) -> int | None:
    item = value.get(key)
    if item is None:
        return None
    if isinstance(item, bool) or not isinstance(item, int):
        raise ValueError(f"{context}.{key} must be an integer or null")
    return item


def _object_string_list(
    value: dict[str, object],
    key: str,
    *,
    context: str,
) -> list[str]:
    item = value.get(key)
    if not isinstance(item, list) or not all(isinstance(entry, str) for entry in item):
        raise ValueError(f"{context}.{key} must be a list of strings")
    return item


def _object_datetime(value: dict[str, object], key: str, *, context: str) -> datetime:
    item = value.get(key)
    if not isinstance(item, str):
        raise ValueError(f"{context}.{key} must be an ISO datetime string")
    parsed = _parse_datetime(item)
    if parsed is None:
        raise ValueError(f"{context}.{key} must not be empty")
    return parsed


def _payload_datetimes(payload: dict[str, object], key: str) -> list[datetime]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"payload.{key} must be a list")
    result: list[datetime] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"payload.{key} must contain ISO datetime strings")
        parsed = _parse_datetime(item)
        if parsed is None:
            raise ValueError(f"payload.{key} contains an empty datetime")
        result.append(parsed)
    return result
