# Agent Memory Contracts

This shard defines what each agent should persist to operational memory through the
Memory Agent policy boundary and what belongs in the structured registry. It is curated
from the Kiro requirements and design docs.

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
operational memory through `MemoryAgentService`. It reads experiment status and metrics
from the registry.

The expected lifecycle is:

```text
NEW -> DATA_VALIDATION -> STATISTICAL_TESTING -> BACKTESTING -> CRITIC_REVIEW -> REPORTING -> FINAL_DECISION
```

## Data Agent

The Data Agent ingests OHLCV data, validates quality, writes datasets to Parquet, and writes
dataset IDs and quality reports to the registry. It writes validation failures and quarantine
decisions to operational memory through `MemoryAgentService`.

Data quality validation must cover UTC timestamp normalization, duplicate timestamps,
missing bars, impossible candles, abnormal volume spikes, deterministic resampling, pair
alignment, provenance, and quality thresholds.

## Hypothesis Agent

The Hypothesis Agent reads market knowledge and past hypotheses from ApeRAG, checks
rejected pairs in the registry, generates candidate pairs with rationale, writes
hypotheses to the registry, and writes only concise rationale summaries to operational
memory through `MemoryAgentService`.

It should request policy-controlled links for similar hypotheses and flag retests of
previously rejected ideas. LLM-generated hypotheses require critic review and budget limits.

## Statistical Testing Agent

The Statistical Testing Agent requires validated datasets before testing. It writes
structured p-values, test statistics, hedge ratios, and related metrics to the registry. It
writes summary lessons and interpretation to operational memory through
`MemoryAgentService`.

## Backtest Agent

The Backtest Agent writes structured performance metrics, gross PnL, net PnL, turnover,
cost attribution, and artifact references to the registry. It writes concise conclusions,
lessons learned, and regime observations to operational memory through
`MemoryAgentService`.

## Critic Agent

The Critic Agent reviews leakage risk, overfitting, weak assumptions, insufficient testing,
unrealistic costs, and decision quality. It writes structured review status to the registry
and policy-safe objections, detected risks, and recommendations to operational memory
through `MemoryAgentService`.

## Report Agent

The Report Agent writes report artifact links and structured report metadata to the
registry. It writes human-readable summaries and manual review notes to operational memory
through `MemoryAgentService`. The registry remains the source of truth for report artifact
paths, formats, metrics, and experiment links. ApeRAG receives only concise report
summaries with registry references, not raw tables or metric-heavy payloads.

## Memory Agent

The Memory Agent owns ApeRAG read/write operations. It reads registry records for IDs and
references but does not write registry rows. It supports topic, entity, and relationship
queries for other agents.

Memory has two layers. Curated project knowledge is the development/architecture memory
seeded from `docs/knowledge/*.md`; it should contain stable contracts, safety rules, and
accepted architecture decisions, not raw development chatter. Operational agent memory is a
separate `stat-arb-agent-memory` collection for runtime lessons, hypotheses, validation
failures, critic reviews, and report summaries. Agents may read curated project knowledge
only for stable rules and contracts. Agent writes must target operational memory through
policy-controlled contracts.

The read boundary is `ApeRAGMemoryClient`: use it for health checks, collection discovery,
document readiness, search, and graph summaries. Runtime writes must pass through
`MemoryAgentService` with `MemoryWriteRequest`; agents must not write raw logs, secrets,
prompts, or metric-heavy payloads directly to ApeRAG.

Use `scripts/check_aperag_agent_memory.ps1` for an end-to-end smoke that creates or checks
the operational collection, writes one policy-approved smoke lesson, waits for indexes, and
verifies search.

## Source References

- `.kiro/specs/quant-research-architecture/requirements.md`
- `.kiro/specs/quant-research-architecture/design.md`
