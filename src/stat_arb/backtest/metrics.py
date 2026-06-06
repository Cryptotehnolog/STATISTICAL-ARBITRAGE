"""Performance metrics for pair backtests."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

from stat_arb.backtest.core import BacktestCoreResult, SpreadPosition


@dataclass(frozen=True)
class PerformanceMetricConfig:
    """Explicit assumptions required for annualized and tail-risk metrics.

    `periods_per_year` and `risk_free_rate_per_period` are deliberately required. The
    backtest layer must not guess whether a strategy uses equities sessions, 24/7 crypto
    periods, or another calendar convention.
    """

    periods_per_year: int
    risk_free_rate_per_period: float
    var_confidence: float
    cvar_confidence: float

    def __post_init__(self) -> None:
        """Validate metric assumptions."""
        if isinstance(self.periods_per_year, bool) or not isinstance(self.periods_per_year, int):
            raise TypeError("periods_per_year must be an integer")
        if self.periods_per_year < 1:
            raise ValueError("periods_per_year must be positive")
        if not np.isfinite(self.risk_free_rate_per_period):
            raise ValueError("risk_free_rate_per_period must be finite")
        if not 0.0 < self.var_confidence < 1.0:
            raise ValueError("var_confidence must be between 0 and 1")
        if not 0.0 < self.cvar_confidence < 1.0:
            raise ValueError("cvar_confidence must be between 0 and 1")


@dataclass(frozen=True)
class ExposureByAssetAndSide:
    """Average absolute exposure by asset and long/short side."""

    asset_a_long: float
    asset_a_short: float
    asset_b_long: float
    asset_b_short: float


@dataclass(frozen=True)
class HoldingTimeMetrics:
    """Holding-time metrics derived from entry/exit transitions."""

    average_holding_time_hours: float
    median_holding_time_hours: float
    completed_holds: int


@dataclass(frozen=True)
class PerformanceMetricsResult:
    """Performance, tail-risk, trade, holding-time, and exposure metrics."""

    sharpe_ratio: float
    sortino_ratio: float
    volatility: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    value_at_risk: float
    conditional_value_at_risk: float
    holding_times: HoldingTimeMetrics
    exposure: ExposureByAssetAndSide
    observations: int


def calculate_performance_metrics(
    *,
    equity_curve: ArrayLike,
    period_returns: ArrayLike,
    trade_pnls: ArrayLike,
    core_result: BacktestCoreResult,
    config: PerformanceMetricConfig,
) -> PerformanceMetricsResult:
    """Calculate backtest performance metrics from explicit inputs."""
    equity = _as_1d_finite_array(equity_curve, name="equity_curve")
    returns = _as_1d_finite_array(period_returns, name="period_returns")
    trades = _as_1d_finite_array(trade_pnls, name="trade_pnls")
    if equity.size < 2:
        raise ValueError("equity_curve requires at least 2 observations")
    if returns.size < 1:
        raise ValueError("period_returns must not be empty")
    if np.any(equity <= 0.0):
        raise ValueError("equity_curve must contain positive values")
    if core_result.observations != equity.size:
        raise ValueError("core_result observations must match equity_curve length")

    return PerformanceMetricsResult(
        sharpe_ratio=_sharpe_ratio(returns, config=config),
        sortino_ratio=_sortino_ratio(returns, config=config),
        volatility=_annualized_volatility(returns, periods_per_year=config.periods_per_year),
        max_drawdown=_max_drawdown(equity),
        win_rate=_win_rate(trades),
        profit_factor=_profit_factor(trades),
        value_at_risk=_tail_loss_quantile(returns, confidence=config.var_confidence),
        conditional_value_at_risk=_conditional_tail_loss(
            returns,
            confidence=config.cvar_confidence,
        ),
        holding_times=_holding_time_metrics(core_result),
        exposure=_exposure_by_asset_and_side(core_result),
        observations=int(equity.size),
    )


def _sharpe_ratio(returns: np.ndarray, *, config: PerformanceMetricConfig) -> float:
    excess_returns = returns - config.risk_free_rate_per_period
    std = float(np.std(excess_returns, ddof=1)) if excess_returns.size > 1 else 0.0
    if std == 0.0:
        return 0.0
    return float((np.mean(excess_returns) / std) * np.sqrt(config.periods_per_year))


def _sortino_ratio(returns: np.ndarray, *, config: PerformanceMetricConfig) -> float:
    excess_returns = returns - config.risk_free_rate_per_period
    downside = excess_returns[excess_returns < 0.0]
    if downside.size == 0:
        return 0.0
    downside_std = float(np.std(downside, ddof=1)) if downside.size > 1 else abs(float(downside[0]))
    if downside_std == 0.0:
        return 0.0
    return float((np.mean(excess_returns) / downside_std) * np.sqrt(config.periods_per_year))


def _annualized_volatility(returns: np.ndarray, *, periods_per_year: int) -> float:
    if returns.size < 2:
        return 0.0
    return float(np.std(returns, ddof=1) * np.sqrt(periods_per_year))


def _max_drawdown(equity: np.ndarray) -> float:
    running_peak = np.maximum.accumulate(equity)
    drawdowns = (running_peak - equity) / running_peak
    return float(np.max(drawdowns))


def _win_rate(trade_pnls: np.ndarray) -> float:
    if trade_pnls.size == 0:
        return 0.0
    return float(np.count_nonzero(trade_pnls > 0.0) / trade_pnls.size)


def _profit_factor(trade_pnls: np.ndarray) -> float:
    gains = float(np.sum(trade_pnls[trade_pnls > 0.0]))
    losses = abs(float(np.sum(trade_pnls[trade_pnls < 0.0])))
    if losses == 0.0:
        return float("inf") if gains > 0.0 else 0.0
    return float(gains / losses)


def _tail_loss_quantile(returns: np.ndarray, *, confidence: float) -> float:
    return float(max(0.0, -np.quantile(returns, 1.0 - confidence)))


def _conditional_tail_loss(returns: np.ndarray, *, confidence: float) -> float:
    threshold = np.quantile(returns, 1.0 - confidence)
    tail = returns[returns <= threshold]
    if tail.size == 0:
        return 0.0
    return float(max(0.0, -np.mean(tail)))


def _holding_time_metrics(core_result: BacktestCoreResult) -> HoldingTimeMetrics:
    durations: list[float] = []
    entry_timestamp = None
    for step in core_result.steps:
        if step.position != SpreadPosition.FLAT and entry_timestamp is None:
            entry_timestamp = step.timestamp
        elif step.position == SpreadPosition.FLAT and entry_timestamp is not None:
            durations.append((step.timestamp - entry_timestamp).total_seconds() / 3600.0)
            entry_timestamp = None

    if not durations:
        return HoldingTimeMetrics(
            average_holding_time_hours=0.0,
            median_holding_time_hours=0.0,
            completed_holds=0,
        )
    duration_array = np.asarray(durations, dtype=float)
    return HoldingTimeMetrics(
        average_holding_time_hours=float(np.mean(duration_array)),
        median_holding_time_hours=float(np.median(duration_array)),
        completed_holds=len(durations),
    )


def _exposure_by_asset_and_side(core_result: BacktestCoreResult) -> ExposureByAssetAndSide:
    positions_a = np.asarray([step.position_a for step in core_result.steps], dtype=float)
    positions_b = np.asarray([step.position_b for step in core_result.steps], dtype=float)
    return ExposureByAssetAndSide(
        asset_a_long=float(np.mean(np.clip(positions_a, 0.0, None))),
        asset_a_short=float(np.mean(np.clip(-positions_a, 0.0, None))),
        asset_b_long=float(np.mean(np.clip(positions_b, 0.0, None))),
        asset_b_short=float(np.mean(np.clip(-positions_b, 0.0, None))),
    )


def _as_1d_finite_array(values: ArrayLike, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array
