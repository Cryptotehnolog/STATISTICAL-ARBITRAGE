# MVP Scope and Constraints

This shard summarizes durable scope rules from the Kiro architecture specs. It is intended
for ApeRAG seeding and should stay smaller than the source design documents.

## V1 Scope

The v1 system is a reproducible statistical arbitrage research platform, not a live trading
system. It must support hypothesis generation, statistical validation, reproducible
backtesting, cost attribution, critic review, reporting, structured experiment storage, and
long-term memory.

V1 focuses on pairs trading only. The primary timeframe is 15-minute bars; 5-minute bars are
secondary after the pipeline is validated. One-minute bars, demo trading, live trading,
streaming infrastructure, enterprise monitoring, and multi-strategy portfolio allocation are
out of scope for the first MVP.

## Hardware Constraints

The system must run on a local Intel i5-1335U PC with 32 GB RAM and no CUDA GPU. It should
also remain compatible with Oracle Cloud Always Free ARM resources. Local development should
prefer simple components that do not require heavy always-on infrastructure.

## Infrastructure Rules

The local MVP must work with Python, uv, SQLite, Parquet, and ApeRAG-backed memory.
Docker is allowed for supporting tools and production-like testing, but it
must not block ordinary local development or pre-commit checks.

Use SQLite or another simple structured registry as the source of truth for numeric metrics,
experiment IDs, dataset IDs, parameters, costs, and final decisions. Use ApeRAG for
summaries, rationale, relationships, lessons learned, and development memory.

## Implementation Bias

Prefer correctness, auditability, and reproducibility over speed. Start with Python reference
implementations. Add Rust only where profiling proves a performance-critical bottleneck and
the API boundary is stable.

## Source References

- `.kiro/specs/quant-research-architecture/requirements.md`
- `.kiro/specs/quant-research-architecture/design.md`
