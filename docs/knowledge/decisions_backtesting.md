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

## DEC-0041: Turnover requires explicit portfolio value

Status: accepted

Decision: Daily turnover is calculated as `traded_value / (elapsed_days *
average_portfolio_value)`. Backtest helpers may return zero turnover when no value is
traded, but they must reject positive traded value unless `average_portfolio_value` is
provided explicitly.

Rationale: Turnover normalizes trading activity by capital. If the engine silently assumes
portfolio value, the same trades can look harmless or excessive depending on an invisible
capital number. Requiring an explicit average portfolio value keeps turnover reproducible
and makes later Critic Agent checks on excessive turnover meaningful.

Alternatives considered: Use gross exposure as implicit portfolio value; use a fixed MVP
capital constant; defer turnover until a full portfolio accounting service exists.

Risks: Early tests need to pass a synthetic capital assumption. That is acceptable in unit
tests, but production backtests must persist the actual capital assumption or portfolio
value source alongside the result.

## DEC-0042: Backtest walk-forward windows require explicit period counts

Status: accepted

Decision: Backtest walk-forward validation uses an explicit `BacktestWalkForwardConfig`
with `train_size`, `test_size`, `step_size`, and `min_folds` expressed in observation
periods. The backtest core does not default to historical planning examples such as 60
training days and 30 testing days.

Rationale: Day-based windows depend on timeframe, calendar, exchange sessions, and missing
data. If the core silently converts days to bars, it can hide assumptions about 15-minute
bars, 24/7 crypto trading, or session calendars. Service and CLI layers may translate
human-readable windows into period counts, but the reusable backtest boundary must receive
the exact counts it will use.

Alternatives considered: Hard-code 60/30 day windows from the planning spec; use the
statistical helper default step behavior; defer walk-forward until the full agent service.

Risks: Operators must choose window sizes explicitly. This is intentional: future Backtest
Agent and Critic Agent checks should evaluate the selected windows rather than inherit
invisible defaults.

## DEC-0043: Performance metrics require explicit annualization assumptions

Status: accepted

Decision: Backtest performance metrics are calculated through a pure
`PerformanceMetricConfig` that requires `periods_per_year`, `risk_free_rate_per_period`,
`var_confidence`, and `cvar_confidence`. The metrics helper does not default to common
calendar examples such as 252 equity sessions, 365 days, or zero risk-free rate.

Rationale: Sharpe, Sortino, volatility, VaR, and CVaR are sensitive to calendar convention,
bar frequency, and risk-free assumptions. The project supports crypto and future equity
workflows, so the core backtest boundary must not guess whether periods represent 24/7
crypto bars, exchange sessions, or another calendar. Services and agents may derive these
assumptions from verified experiment configuration, but the pure metrics helper receives
the exact values used.

Alternatives considered: Hard-code annualization constants in the helper; use zero
risk-free rate by default; defer metrics until registry persistence exists.

Risks: Early tests need synthetic explicit configs. That verbosity is acceptable because it
prevents future agents from treating examples as production assumptions.

## DEC-0044: Cost sensitivity scenarios are explicit inputs

Status: accepted

Decision: Backtest cost sensitivity analysis runs through explicit
`CostSensitivityScenario` inputs. The common 2x-cost and 0.5x-cost checks from the task
plan are useful required scenarios for MVP validation, but they are not hidden runtime
defaults inside the helper.

Rationale: Sensitivity analysis is a comparison boundary, not a source of market truth.
Future agents should choose and persist the exact stress scenarios used for a backtest,
including scenario names and multipliers. Keeping scenarios explicit prevents reports from
silently changing when a helper default changes.

Alternatives considered: Hard-code 2x and 0.5x scenarios in the function; run only one
manual stress case; defer sensitivity analysis until the reporting layer.

Risks: Callers must pass scenario tuples even for standard MVP checks. That is intentional:
experiment config and registry persistence should record the scenarios actually used.

## DEC-0045: Baseline comparisons require explicit baseline contracts

Status: accepted

Decision: Backtest baseline comparison is implemented through explicit baseline config
objects. Buy-and-hold baselines require a name, selected asset, side, units, and initial
capital. Random spread-entry baselines require a name, hedge ratio, seed, entry
probability, and initial capital. The comparison result persists baseline identity,
baseline kind, generated baseline returns, generated positions, strategy Sharpe, baseline
Sharpe, and Sharpe delta.

Rationale: Baselines affect whether a strategy appears to generate alpha. A hidden asset,
side, seed, capital assumption, or entry probability can make an agent compare against a
weak or irreproducible reference strategy. Keeping the baseline contract explicit lets
future reports and registry records show exactly what the strategy was compared against.

Alternatives considered: Hard-code a long asset-A buy-and-hold baseline; use a random
baseline with an internal seed; compare only raw returns without storing baseline
configuration.

Risks: Baseline calls are more verbose. This is acceptable because agents must not inherit
planning examples or convenient hidden values when assessing strategy quality.

## DEC-0046: Reproducibility manifests hash all research assumptions

Status: accepted

Decision: Backtest experiment reproducibility uses an immutable manifest with git commit
hash, stable config hash, dataset IDs, optional random seed, execution command, run
timestamp, and dependency lock file hash. The config hash is calculated from explicit
configuration components supplied by the caller, so baseline config, metric config, cost
config, sensitivity scenarios, and future research assumptions can all be included in one
canonical SHA-256 hash.

Rationale: Recording only a top-level config name or a partial parameter subset would let a
rerun be "almost the same" while silently changing baseline, cost, risk, or sensitivity
assumptions. A canonical config hash makes those changes visible and gives the registry a
compact reproducibility key.

Alternatives considered: Store only git commit and dataset IDs; hash a raw YAML file
without normalizing structured Python configs; defer reproducibility until registry
integration.

Risks: Callers must assemble the complete config component mapping. This is intentional:
the Backtest Agent service owns that assembly before writing to the registry or memory.

## DEC-0047: Backtest Agent writes registry first and memory through policy

Status: accepted

Decision: The first Backtest Agent integration boundary persists completed backtest
outputs to the Structured Registry and writes only a concise report summary through a
`MemoryAgentService`-compatible writer. The agent boundary verifies passed data-quality
reports and a passed statistical test before persistence. It does not import
`ApeRAGMemoryClient` and does not write directly to ApeRAG.

Rationale: Numeric performance metrics, cost attribution, baseline Sharpe, and
reproducibility hashes belong in the registry as the source of truth. ApeRAG should receive
short lessons and summaries only through Memory Agent policy checks, so agents cannot
accidentally store raw metrics, logs, prompts, or secrets in long-term memory.

Alternatives considered: Let Backtest Agent write directly to ApeRAG; defer registry writes
until reporting; combine full backtest execution, persistence, and reporting in one large
agent.

Risks: The boundary currently persists completed results produced by earlier pure helpers;
future orchestration still needs to assemble those inputs and handle failed backtests.

## DEC-0048: Backtest edge cases are checkpoint blockers despite optional task marker

Status: accepted

Decision: Backtest edge-case tests cover always-flat empty trade sequences, single open
trades, extreme explicit cost snapshots, and missing required sensitivity scenarios. A
manual `scripts/check_backtest_pipeline.ps1` command runs the core, PnL, metrics, baseline,
sensitivity, reproducibility, and Backtest Agent boundary tests together.

Rationale: Task 7.12 is marked optional in the planning file, but after registry and memory
integration it is cheap and valuable to prove edge behavior before checkpoint 8. These
tests protect against fake activity in no-trade backtests, broken accounting for open
positions, cost-conservation failures under stress assumptions, and reports missing the
required MVP sensitivity comparison.

Alternatives considered: Skip optional edge tests until the reporting layer; rely only on
property tests; test the whole pipeline only through the future CLI.

Risks: The check script is still a test aggregation command, not a production backtest CLI.
The future CLI must add real dataset loading, config parsing, registry IDs, and operator
output.

## DEC-0049: Backtest signals execute on the next bar

Status: accepted

Decision: `run_pair_backtest_core` treats the z-score observed at bar `t` as a signal that
can change position only at bar `t+1`. Each step still records the current bar's z-score
for auditability, but action decisions use the previous finite signal.

Rationale: Same-bar execution can encode lookahead when the signal is computed from the
current close. Next-bar execution is the conservative default for research correctness and
matches the Critic Agent's strict lookahead-bias policy.

Alternatives considered: Keep same-bar execution and rely on callers to shift signals.
That is too easy for agents to misuse.

Risks: Backtest results may become less optimistic after this change. That is desirable:
the engine should not reward unavailable information.

## DEC-0050: Backtest persistence verifies full statistical-test provenance

Status: accepted

Decision: `run_backtest_agent_persistence` now requires the passed statistical test row to
match the requested `hypothesis_id`, `dataset_a_id`, and `dataset_b_id`, not merely the
provided `test_id`.

Rationale: A valid statistical-test row from one experiment must not authorize an
unrelated backtest. Registry IDs form a chain of custody from hypothesis to datasets to
statistical test to backtest.

Alternatives considered: Trust foreign-key existence and the caller's request payload.
That permits provenance splicing by mistake or by a faulty agent.

Risks: Tests and future services must seed prerequisites consistently. This is intentional
because reproducible experiments need a strict chain.
