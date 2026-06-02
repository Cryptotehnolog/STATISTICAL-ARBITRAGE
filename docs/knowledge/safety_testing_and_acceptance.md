# Safety, Testing, and Acceptance Contracts

This shard summarizes quality gates, error handling, and MVP acceptance criteria from the
Kiro specs.

## Error Handling

Data outages, data quality failures, stale data, failed statistical tests, regime changes,
runtime errors, negative net PnL, excessive turnover, LLM timeouts, invalid LLM outputs,
tool permission violations, database failures, RAG failures, and secrets failures must be
handled explicitly.

Retry API and LLM failures with bounded exponential backoff. If retries are exhausted,
fallback to deterministic logic where possible. Unauthorized tool use should be rejected
and logged as a security event.

## Hard Stops

Demo/live hard stops are future-scope, but research code should already model safety
thinking. Hard stop examples include max drawdown breach, repeated execution errors, stale
data, unexpected exposure, and runaway order generation.

Research workflows should quarantine affected experiments and require human review after
critical failures.

## Testing Strategy

The codebase should keep a fast unit baseline for ordinary commits. Property tests are
recommended for statistical and data-quality invariants, including timestamp normalization,
missing bar detection, duplicate detection, outlier sensitivity, resampling idempotence,
timestamp alignment, cointegration accuracy, ADF detection, half-life estimation, z-score
properties, PnL conservation, turnover consistency, risk compliance, and reproducibility.

LLM and OmniRoute checks should remain separate from the ordinary pre-commit check because
they depend on external service state.

## MVP Acceptance

The MVP is complete when the project can initialize the repository and local infrastructure,
ingest and validate at least one data source, run at least one scripted pair-screening
workflow, run statistical testing and backtesting workflows, write structured records to the
registry, write concise summaries to LightRAG, show experiments through a dashboard or
report view, and pass CI.

Non-functional acceptance includes local PC support, Oracle Cloud Always Free compatibility,
reasonable memory and disk usage, no paid data dependency in v1, Infisical-managed secrets,
and a full experiment runtime target suitable for iterative research.

## Source References

- `.kiro/specs/quant-research-architecture/requirements.md`
- `.kiro/specs/quant-research-architecture/design.md`
- `.kiro/specs/quant-research-architecture/tasks.md`
