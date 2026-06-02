# Research Workflow Contracts

This shard summarizes the core research workflow contracts that should guide implementation.

## Data Quality Before Research

No statistical test or backtest should run before a data quality report exists. The data
pipeline must normalize timestamps to UTC, reject duplicate timestamps, detect missing bars,
flag impossible candles and abnormal volume spikes, align pair timestamps, and store
provenance.

Raw market data belongs in Parquet. Dataset metadata and quality report references belong in
the structured registry. Only validation failures, quarantine decisions, and concise lessons
belong in LightRAG.

## Hypothesis Flow

A hypothesis contains an ID, asset pair, rationale, source, similar hypothesis references,
novelty score, and timestamp. The Hypothesis Agent should check LightRAG for similar prior
hypotheses and the registry for invalidated pairs before creating a new candidate.

Retests of rejected hypotheses require explicit justification. Similar hypotheses should be
linked in LightRAG.

## Statistical Testing Flow

The Statistical Testing Agent performs Engle-Granger cointegration tests, ADF residual
stationarity checks, hedge ratio estimation, half-life estimation, z-score construction,
multiple-testing correction, regime-change checks, and walk-forward validation.

Structured values belong in the registry. LightRAG receives a summary lesson explaining why
the hypothesis passed, failed, or needs retesting.

## Backtest Flow

The Backtest Agent uses validated data and tested hypotheses. It tracks signals, positions,
gross PnL, net PnL, commissions, spread cost, slippage, funding cost, borrow cost, turnover,
equity curve, drawdown, and report artifacts.

The registry stores the numbers and artifact references. LightRAG stores conclusions,
lessons learned, and notable regime/cost observations.

## Critic Flow

The Critic Agent must check for lookahead bias, future information in signals, overlapping
walk-forward windows, overfitting, weak assumptions, insufficient test coverage, negative
net PnL after costs, excessive turnover, and unrealistic slippage.

Critical issues cause rejection. Moderate issues may quarantine the experiment. Approved
results still require human review before any demo-trading step.

## Source References

- `.kiro/specs/quant-research-architecture/requirements.md`
- `.kiro/specs/quant-research-architecture/design.md`
- `.kiro/specs/quant-research-architecture/tasks.md`
