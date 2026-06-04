# Knowledge Decisions: Backtesting

This shard contains durable decisions about Backtest Agent contracts, signal generation,
position tracking, cost attribution, performance metrics, and reproducibility.

## DEC-0039: Keep the first backtest core pure and aligned-data only

Status: accepted

Decision: Implement the first Backtest Agent boundary as a pure `stat_arb.backtest` core
that accepts already aligned timestamps, asset A prices, asset B prices, z-scores, hedge
ratio, and entry/exit thresholds. The core emits deterministic position steps and trade
transitions without writing to the registry or ApeRAG.

Rationale: Backtesting should not bypass the data-quality and pair-alignment boundaries
created earlier in the pipeline. Keeping signal and position construction pure lets later
tasks add PnL, cost attribution, turnover, walk-forward windows, performance metrics,
registry persistence, and Memory Agent summaries without mixing those concerns into one
large service.

Signal convention: A positive z-score means the spread is expensive, so the strategy enters
`short_spread`: short asset A and long `hedge_ratio` units of asset B. A negative z-score
means the spread is cheap, so the strategy enters `long_spread`: long asset A and short
`hedge_ratio` units of asset B. Positions exit when `abs(z_score)` is at or below the
configured exit threshold.

Alternatives considered: Build PnL, costs, registry writes, and memory writes in the first
backtest function; accept raw OHLCV batches and perform alignment inside backtesting; defer
position tracking until PnL exists.

Risks: The pure core proves chronological aligned inputs by shape and timestamp checks, but
the future service layer must still require passed data-quality reports and alignment
provenance before calling it.

## DEC-0040: No hidden default costs in backtesting

Status: accepted

Decision: Backtest PnL and cost attribution must require an explicit cost assumption
snapshot. Commission, spread cost, slippage, funding, and borrow rates are not hidden
runtime defaults. Historical planning values from `.kiro/tasks.md` are not trusted cost
assumptions and must not be used by agents as real market data.

Rationale: Costs are market, venue, account-tier, instrument, liquidity, and time dependent.
Using planning placeholders as defaults would let future agents produce attractive but
unreproducible backtests. Every cost config must carry provenance, verification time,
venue, market type, and status. Backtests may use only `verified` or explicitly
`manual_approved` cost snapshots.

Alternatives considered: Keep old MVP defaults in the engine; use zero costs when a rate is
unknown; let the Backtest Agent silently fall back to planning assumptions.

Risks: Requiring explicit costs makes early tests more verbose, but it prevents agents from
mistaking stale planning text for real exchange fees. A future Cost Assumption Agent should
collect, verify, store, and refresh exchange-specific cost snapshots before production
backtests.
