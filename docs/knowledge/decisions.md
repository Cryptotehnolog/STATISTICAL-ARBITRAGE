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
  validation, registry persistence.
- `docs/knowledge/decisions_data_transforms.md`: resampling, deterministic dataset IDs,
  pair alignment, data property tests, and data-pipeline checkpoints.
- `docs/knowledge/decisions_statistical_testing.md`: Engle-Granger cointegration,
  multiple-testing correction, and Statistical Testing Agent boundaries.
- `docs/knowledge/decisions_backtesting.md`: Backtest Agent signal generation, position
  tracking, cost attribution, performance metrics, and reproducibility boundaries.
- `docs/knowledge/decisions_critic_agent.md`: Critic Agent policies and review
  boundaries.
- `docs/knowledge/decisions_reporting.md`: Report Agent artifact generation, registry
  persistence, and memory-summary boundaries.
- `docs/knowledge/decisions_coordinator_agent.md`: Coordinator Agent lifecycle,
  registry persistence, and memory-policy boundaries.
- `docs/knowledge/decisions_failure_handling.md`: failure handling, safe mode,
  retry/backoff, and local runtime budget boundaries.
- `docs/knowledge/decisions_expert_review_hardening.md`: external expert review outcomes,
  explicit threshold policy, memory backend resilience, and research hardening scope.
- `docs/knowledge/decisions_future_paper_live.md`: staged future paper/live trading
  roles, execution realism, regime monitoring, and capital allocation boundaries.
- `docs/knowledge/decisions_multi_asset_roadmap.md`: staged multi-asset roadmap,
  asset-class onboarding rules, factor exposure, and rejected premature execution paths.

## Operating Rule

New decisions must be added to the smallest relevant thematic shard. Add a new shard only
when a topic becomes large enough to slow or muddy graph extraction.
