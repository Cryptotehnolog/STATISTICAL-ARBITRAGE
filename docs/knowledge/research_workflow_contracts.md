# Research Workflow Contracts

This shard summarizes the core research workflow contracts that should guide implementation.

## Data Quality Before Research

No statistical test or backtest should run before a data quality report exists. The data
pipeline must normalize timestamps to UTC, reject duplicate timestamps, detect missing bars,
flag impossible candles and abnormal volume spikes, align pair timestamps, and store
provenance.

Raw market data belongs in Parquet. Dataset metadata and quality report references belong in
the structured registry. Only validation failures, quarantine decisions, and concise lessons
belong in ApeRAG.

## Hypothesis Flow

A hypothesis contains an ID, asset pair, rationale, source, similar hypothesis references,
novelty score, and timestamp. The Hypothesis Agent should check ApeRAG for similar prior
hypotheses and the registry for invalidated pairs before creating a new candidate.

Retests of rejected hypotheses require explicit justification. Similar hypotheses should be
linked in ApeRAG.

## Statistical Testing Flow

The Statistical Testing Agent performs Engle-Granger cointegration tests, ADF residual
stationarity checks, hedge ratio estimation, half-life estimation, z-score construction,
multiple-testing correction, regime-change checks, and walk-forward validation.

Structured values belong in the registry. ApeRAG receives a summary lesson explaining why
the hypothesis passed, failed, or needs retesting.

## Backtest Flow

The Backtest Agent uses validated data and tested hypotheses. It tracks signals, positions,
gross PnL, net PnL, commissions, spread cost, slippage, funding cost, borrow cost, turnover,
equity curve, drawdown, and report artifacts.

Cost inputs must come from explicit `verified` or `manual_approved` cost snapshots with
provenance. Historical planning percentages are not trusted cost assumptions and must not
be used as runtime defaults.

The registry stores the numbers and artifact references. ApeRAG stores conclusions,
lessons learned, and notable regime/cost observations.

## Scripted CLI Workflow Checkpoint

Task 15 scripted workflows are small wrappers around mature CLI and agent boundaries, not a
single autonomous "run everything" button. Pair screening writes hypotheses through the
Hypothesis Agent boundary. Statistical testing and backtesting are queued and executed
through Coordinator-backed `experiment run-stage` and `experiment execute-stage` commands.
Reporting is allowed only when a matching factual `backtest_series` sidecar exists.

`tests/integration/test_cli_scripted_workflows.py` is the current end-to-end mock-data
checkpoint for this chain. It proves that scripts compose through the registry and
Coordinator task queue while keeping Report Agent sidecar guards active. It does not fetch
live market data, call external LLM providers, or replace the future full experiment
runner.

Task 19.5 documents the same real entrypoints in `docs/examples.md`. Documentation must not
advertise script paths or `stat-arb` subcommands that are not present in the repository;
`scripts/check_docs_links.ps1` guards this user-facing surface.

## Defaults Policy

Hidden research defaults are not allowed when a value changes statistical conclusions,
backtest results, risk interpretation, costs, capital normalization, calendar assumptions,
baseline behavior, or agent decisions. Those values must be explicit, verified, or selected
through a named persisted preset that is included in the experiment config hash.

Technical defaults are allowed when they do not change research conclusions. Examples
include dry-run behavior, local cache paths, page sizes, UI sort order, log verbosity,
timeouts, and bounded retry counts.

Presets are allowed only when they have a clear name, are visible to the operator, are
persisted with the experiment, and are treated as configuration rather than market truth.
Agents must not treat old planning examples as verified parameters.

## Critic Flow

The Critic Agent must check for lookahead bias, future information in signals, overlapping
walk-forward windows, overfitting, weak assumptions, residual diagnostics, insufficient
test coverage, negative net PnL after costs, excessive turnover, and unrealistic slippage.

Critical issues cause rejection. Moderate issues may quarantine the experiment. Approved
results still require human review before any demo-trading step.

## Source References

- `.kiro/specs/quant-research-architecture/requirements.md`
- `.kiro/specs/quant-research-architecture/design.md`
- `.kiro/specs/quant-research-architecture/tasks.md`
