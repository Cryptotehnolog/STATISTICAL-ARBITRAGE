"""Opt-in live market-data acceptance smoke for public CCXT OHLCV endpoints."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

FetchOHLCV = Callable[[str, str, int], list[list[Any]]]
PREFERRED_ACCEPTANCE_BASES = ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA", "LINK", "AVAX", "LTC")


@dataclass(frozen=True)
class LiveMarketDataAcceptanceConfig:
    """Configuration for the live market-data acceptance smoke."""

    exchange_id: str = "bybit"
    asset_count: int = 50
    min_successful_assets: int = 50
    bars_per_asset: int = 2
    timeframe: str = "15m"
    quote_asset: str = "USDT"
    market_type: str = "swap"
    output_json: Path | None = Path("data/live_market_data_acceptance/report.json")

    def __post_init__(self) -> None:
        if self.asset_count < 1:
            raise ValueError("asset_count must be at least 1")
        if self.min_successful_assets < 1:
            raise ValueError("min_successful_assets must be at least 1")
        if self.min_successful_assets > self.asset_count:
            raise ValueError("min_successful_assets cannot exceed asset_count")
        if self.bars_per_asset < 1:
            raise ValueError("bars_per_asset must be at least 1")
        if self.market_type not in {"swap", "spot", "future", "any"}:
            raise ValueError("market_type must be one of: swap, spot, future, any")


@dataclass(frozen=True)
class LiveMarketDataAssetResult:
    """Per-symbol result for the live market-data acceptance smoke."""

    symbol: str
    row_count: int
    passed: bool
    error: str | None = None


@dataclass(frozen=True)
class LiveMarketDataAcceptanceReport:
    """Serializable acceptance report for live market-data readiness."""

    exchange_id: str
    generated_at: str
    asset_count: int
    min_successful_assets: int
    successful_assets: int
    failed_assets: int
    selected_assets: list[str]
    results: list[LiveMarketDataAssetResult]
    passed: bool


def _market_matches_type(market: Mapping[str, Any], market_type: str) -> bool:
    if market_type == "any":
        return True
    return bool(market.get(market_type))


def select_symbols_for_acceptance(
    markets: Mapping[str, Mapping[str, Any]],
    *,
    quote_asset: str,
    market_type: str,
    asset_count: int,
) -> list[str]:
    """Select deterministic active symbols for the live acceptance smoke."""
    quote = quote_asset.upper()
    symbols: list[str] = []

    for market_id, market in markets.items():
        symbol = str(market.get("symbol") or market_id)
        if market.get("active") is False:
            continue
        if str(market.get("quote", "")).upper() != quote:
            continue
        if not _market_matches_type(market, market_type):
            continue
        symbols.append(symbol)

    unique_symbols = sorted(set(symbols))
    preferred: list[str] = []
    remaining = unique_symbols.copy()
    for base in PREFERRED_ACCEPTANCE_BASES:
        prefix = f"{base}/"
        matches = [symbol for symbol in remaining if symbol.startswith(prefix)]
        preferred.extend(matches)
        remaining = [symbol for symbol in remaining if symbol not in matches]

    return [*preferred, *remaining][:asset_count]


def build_live_market_data_acceptance_report(
    config: LiveMarketDataAcceptanceConfig,
    markets: Mapping[str, Mapping[str, Any]],
    fetch_ohlcv: FetchOHLCV,
) -> LiveMarketDataAcceptanceReport:
    """Build and optionally persist a live market-data acceptance report."""
    selected_assets = select_symbols_for_acceptance(
        markets,
        quote_asset=config.quote_asset,
        market_type=config.market_type,
        asset_count=config.asset_count,
    )
    results: list[LiveMarketDataAssetResult] = []

    for symbol in selected_assets:
        try:
            rows = fetch_ohlcv(symbol, config.timeframe, config.bars_per_asset)
            row_count = len(rows)
            results.append(
                LiveMarketDataAssetResult(
                    symbol=symbol,
                    row_count=row_count,
                    passed=row_count >= config.bars_per_asset,
                )
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                LiveMarketDataAssetResult(
                    symbol=symbol,
                    row_count=0,
                    passed=False,
                    error=str(exc),
                )
            )

    successful_assets = sum(1 for result in results if result.passed)
    failed_assets = len(selected_assets) - successful_assets
    report = LiveMarketDataAcceptanceReport(
        exchange_id=config.exchange_id,
        generated_at=datetime.now(UTC).isoformat(),
        asset_count=config.asset_count,
        min_successful_assets=config.min_successful_assets,
        successful_assets=successful_assets,
        failed_assets=failed_assets,
        selected_assets=selected_assets,
        results=results,
        passed=successful_assets >= config.min_successful_assets,
    )

    if config.output_json is not None:
        config.output_json.parent.mkdir(parents=True, exist_ok=True)
        config.output_json.write_text(
            json.dumps(asdict(report), indent=2, sort_keys=True),
            encoding="utf-8",
        )

    return report


def _create_ccxt_exchange(exchange_id: str) -> Any:
    import ccxt  # noqa: PLC0415

    exchange_class = getattr(ccxt, exchange_id, None)
    if exchange_class is None:
        raise ValueError(f"Unsupported CCXT exchange: {exchange_id}")
    return exchange_class({"enableRateLimit": True})


def run_live_market_data_acceptance(config: LiveMarketDataAcceptanceConfig) -> LiveMarketDataAcceptanceReport:
    """Run the live acceptance smoke against a real CCXT exchange."""
    exchange = _create_ccxt_exchange(config.exchange_id)
    markets = exchange.load_markets()

    def fetch_ohlcv(symbol: str, timeframe: str, limit: int) -> list[list[Any]]:
        return cast(list[list[Any]], exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit))

    return build_live_market_data_acceptance_report(config, markets, fetch_ohlcv)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exchange-id", default="bybit")
    parser.add_argument("--asset-count", type=int, default=50)
    parser.add_argument("--min-successful-assets", type=int, default=50)
    parser.add_argument("--bars-per-asset", type=int, default=2)
    parser.add_argument("--timeframe", default="15m")
    parser.add_argument("--quote-asset", default="USDT")
    parser.add_argument("--market-type", choices=["swap", "spot", "future", "any"], default="swap")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("data/live_market_data_acceptance/report.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    config = LiveMarketDataAcceptanceConfig(
        exchange_id=args.exchange_id,
        asset_count=args.asset_count,
        min_successful_assets=args.min_successful_assets,
        bars_per_asset=args.bars_per_asset,
        timeframe=args.timeframe,
        quote_asset=args.quote_asset,
        market_type=args.market_type,
        output_json=args.output_json,
    )
    report = run_live_market_data_acceptance(config)
    print(json.dumps(asdict(report), indent=2, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
