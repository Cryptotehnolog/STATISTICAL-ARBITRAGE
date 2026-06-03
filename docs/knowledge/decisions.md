# Knowledge Decisions Index

This file is the navigation index for durable project decisions seeded into ApeRAG.
Keep detailed decisions in focused thematic shards so graph extraction stays clear and
regular memory updates do not reprocess one oversized document.

## Decision Shards

- `docs/knowledge/decisions_memory_aperag.md`: ApeRAG, curated memory,
  OmniRoute, memory-agent boundaries.
- `docs/knowledge/decisions_infra_ci_secrets.md`: runtime layout, Infisical, GitHub Actions,
  local-first infrastructure constraints.
- `docs/knowledge/decisions_data_pipeline.md`: domain contracts, CCXT ingestion, OHLCV
  validation, registry persistence, resampling.
- `docs/knowledge/decisions_statistical_testing.md`: Engle-Granger cointegration,
  multiple-testing correction, and Statistical Testing Agent boundaries.

## Operating Rule

New decisions must be added to the smallest relevant thematic shard. Add a new shard only
when a topic becomes large enough to slow or muddy graph extraction.
