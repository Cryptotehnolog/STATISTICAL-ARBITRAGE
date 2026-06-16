"""Unit tests for opt-in live market-data acceptance checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stat_arb.scripts.check_live_market_data_acceptance import (
    LiveMarketDataAcceptanceConfig,
    build_live_market_data_acceptance_report,
    select_symbols_for_acceptance,
)


def test_select_symbols_prefers_active_usdt_swaps_for_bybit_acceptance() -> None:
    """The acceptance candidate set should match the documented Bybit-first startup policy."""
    markets: dict[str, dict[str, Any]] = {
        "BTC/USDT:USDT": {"symbol": "BTC/USDT:USDT", "quote": "USDT", "active": True, "swap": True},
        "ETH/USDT:USDT": {"symbol": "ETH/USDT:USDT", "quote": "USDT", "active": True, "swap": True},
        "DOGE/USDC:USDC": {"symbol": "DOGE/USDC:USDC", "quote": "USDC", "active": True, "swap": True},
        "XRP/USDT": {"symbol": "XRP/USDT", "quote": "USDT", "active": True, "spot": True},
        "SOL/USDT:USDT": {"symbol": "SOL/USDT:USDT", "quote": "USDT", "active": False, "swap": True},
    }

    selected = select_symbols_for_acceptance(
        markets,
        quote_asset="USDT",
        market_type="swap",
        asset_count=2,
    )

    assert selected == ["BTC/USDT:USDT", "ETH/USDT:USDT"]


def test_live_market_data_acceptance_requires_all_selected_assets(tmp_path: Path) -> None:
    """A report should fail closed when not enough selected assets produce OHLCV rows."""
    config = LiveMarketDataAcceptanceConfig(
        exchange_id="bybit",
        asset_count=3,
        min_successful_assets=3,
        bars_per_asset=2,
        timeframe="15m",
        quote_asset="USDT",
        market_type="swap",
        output_json=tmp_path / "report.json",
    )
    markets: dict[str, dict[str, Any]] = {
        "BTC/USDT:USDT": {"symbol": "BTC/USDT:USDT", "quote": "USDT", "active": True, "swap": True},
        "ETH/USDT:USDT": {"symbol": "ETH/USDT:USDT", "quote": "USDT", "active": True, "swap": True},
        "SOL/USDT:USDT": {"symbol": "SOL/USDT:USDT", "quote": "USDT", "active": True, "swap": True},
    }

    def fake_fetch(symbol: str, timeframe: str, limit: int) -> list[list[float]]:
        assert timeframe == "15m"
        assert limit == 2
        if symbol == "SOL/USDT:USDT":
            raise TimeoutError("temporary upstream error")
        return [
            [1.0, 100.0, 101.0, 99.0, 100.5, 10.0],
            [2.0, 100.5, 101.5, 99.5, 101.0, 12.0],
        ]

    report = build_live_market_data_acceptance_report(config, markets, fake_fetch)

    assert report.passed is False
    assert report.successful_assets == 2
    assert report.failed_assets == 1
    assert report.selected_assets == ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]
    assert report.results[-1].error == "temporary upstream error"
    assert config.output_json is not None
    persisted = json.loads(config.output_json.read_text(encoding="utf-8"))
    assert persisted["passed"] is False


def test_live_market_data_acceptance_rejects_hidden_small_defaults() -> None:
    """The public script defaults should encode the documented 50-asset handoff smoke."""
    config = LiveMarketDataAcceptanceConfig(output_json=None)

    assert config.exchange_id == "bybit"
    assert config.asset_count == 50
    assert config.min_successful_assets == 50
    assert config.bars_per_asset == 2


def test_live_market_data_acceptance_is_not_part_of_pre_commit() -> None:
    """Live exchange calls must remain opt-in and outside deterministic local checks."""
    pre_commit = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")

    assert "check_live_market_data_acceptance.ps1" not in pre_commit
