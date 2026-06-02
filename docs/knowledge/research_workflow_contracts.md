# Контракты research workflow

Этот shard кратко фиксирует core research workflow contracts, которые должны направлять
implementation.

## Data quality до research

Ни один statistical test или backtest не должен запускаться до появления data quality
report. Data pipeline обязан нормализовать timestamps в UTC, отклонять duplicate
timestamps, находить missing bars, помечать impossible candles и abnormal volume spikes,
выравнивать pair timestamps и хранить provenance.

Raw market data хранится в Parquet. Dataset metadata и ссылки на quality reports хранятся в
structured registry. В LightRAG попадают только validation failures, quarantine decisions и
краткие lessons.

## Hypothesis flow

Hypothesis содержит ID, asset pair, rationale, source, ссылки на похожие hypotheses, novelty
score и timestamp. Hypothesis Agent должен проверять LightRAG на похожие прошлые hypotheses
и registry на invalidated pairs до создания нового candidate.

Retests отклоненных hypotheses требуют явного justification. Similar hypotheses должны быть
связаны в LightRAG.

## Statistical testing flow

Statistical Testing Agent выполняет Engle-Granger cointegration tests, ADF residual
stationarity checks, hedge ratio estimation, half-life estimation, z-score construction,
multiple-testing correction, regime-change checks и walk-forward validation.

Structured values хранятся в registry. LightRAG получает summary lesson, объясняющий,
почему hypothesis прошла, провалилась или требует retesting.

## Backtest flow

Backtest Agent использует validated data и tested hypotheses. Он отслеживает signals,
positions, gross PnL, net PnL, commissions, spread cost, slippage, funding cost, borrow cost,
turnover, equity curve, drawdown и report artifacts.

Registry хранит числа и artifact references. LightRAG хранит conclusions, lessons learned и
важные regime/cost observations.

## Critic flow

Critic Agent обязан проверять lookahead bias, future information in signals, overlapping
walk-forward windows, overfitting, weak assumptions, insufficient test coverage, negative net
PnL after costs, excessive turnover и unrealistic slippage.

Critical issues приводят к rejection. Moderate issues могут отправить experiment в
quarantine. Даже approved results требуют human review перед любым demo-trading step.

## Источники

- `.kiro/specs/quant-research-architecture/requirements.md`
- `.kiro/specs/quant-research-architecture/design.md`
- `.kiro/specs/quant-research-architecture/tasks.md`
