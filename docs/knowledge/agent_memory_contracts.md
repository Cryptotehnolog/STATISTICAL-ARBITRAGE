# Agent Memory Contracts

This shard defines what each agent should write to ApeRAG and what belongs in the
structured registry. It is curated from the Kiro requirements and design docs.

## Shared Rule

ApeRAG stores high-level memory: rationale, lessons, decisions, summaries, relationships,
manual notes, and code references. It must not store raw logs, raw prompts, secrets, large
datasets, OHLCV data, or precise numeric metrics that belong in the structured registry.

The structured registry is the source of truth for experiment IDs, dataset IDs, parameters,
p-values, test statistics, backtest metrics, costs, artifacts, review states, and final
decisions.

## Coordinator Agent

The Coordinator Agent manages the task queue and experiment lifecycle. It writes lifecycle
events, final decisions, rejection reasons, promotion reasons, and registry links to
ApeRAG. It reads experiment status and metrics from the registry.

The expected lifecycle is:

```text
NEW -> DATA_VALIDATION -> STATISTICAL_TESTING -> BACKTESTING -> CRITIC_REVIEW -> REPORTING -> FINAL_DECISION
```

## Data Agent

The Data Agent ingests OHLCV data, validates quality, writes datasets to Parquet, and writes
dataset IDs and quality reports to the registry. It writes validation failures and quarantine
decisions to ApeRAG.

Data quality validation must cover UTC timestamp normalization, duplicate timestamps,
missing bars, impossible candles, abnormal volume spikes, deterministic resampling, pair
alignment, provenance, and quality thresholds.

## Hypothesis Agent

The Hypothesis Agent reads market knowledge and past hypotheses from ApeRAG, checks
rejected pairs in the registry, generates candidate pairs with rationale, and writes
hypotheses to both ApeRAG and the registry.

It should link similar hypotheses in ApeRAG and flag retests of previously rejected ideas.
LLM-generated hypotheses require critic review and budget limits.

## Statistical Testing Agent

The Statistical Testing Agent requires validated datasets before testing. It writes
structured p-values, test statistics, hedge ratios, and related metrics to the registry. It
writes summary lessons and interpretation to ApeRAG.

## Backtest Agent

The Backtest Agent writes structured performance metrics, gross PnL, net PnL, turnover,
cost attribution, and artifact references to the registry. It writes concise conclusions,
lessons learned, and regime observations to ApeRAG.

## Critic Agent

The Critic Agent reviews leakage risk, overfitting, weak assumptions, insufficient testing,
unrealistic costs, and decision quality. It writes objections, detected risks, review status,
and recommendations to ApeRAG and the registry.

## Report Agent

The Report Agent writes report artifact links and structured report metadata to the
registry. It writes human-readable summaries and manual review notes to ApeRAG.

## Memory Agent

The Memory Agent owns ApeRAG read/write operations. It reads registry records for IDs and
references but does not write registry rows. It supports topic, entity, and relationship
queries for other agents.

Memory has two layers. Curated project knowledge is the development/architecture memory
seeded from `docs/knowledge/*.md`. Operational agent memory is a separate write layer for
runtime lessons, hypotheses, validation failures, critic reviews, and report summaries.
Agents may read curated project knowledge, but agent writes must target operational memory
through policy-controlled contracts.

The read boundary is `ApeRAGMemoryClient`: use it for health checks, collection discovery,
document readiness, search, and graph summaries. Runtime writes must pass through
`MemoryAgentService` with `MemoryWriteRequest`; agents must not write raw logs, secrets,
prompts, or metric-heavy payloads directly to ApeRAG.

## Source References

- `.kiro/specs/quant-research-architecture/requirements.md`
- `.kiro/specs/quant-research-architecture/design.md`
