# Контракты safety, testing и acceptance

Этот shard кратко фиксирует quality gates, error handling и MVP acceptance criteria из Kiro
specs.

## Error handling

Data outages, data quality failures, stale data, failed statistical tests, regime changes,
runtime errors, negative net PnL, excessive turnover, LLM timeouts, invalid LLM outputs,
tool permission violations, database failures, RAG failures и secrets failures должны
обрабатываться явно.

API и LLM failures нужно retry с bounded exponential backoff. Если retries exhausted, где
возможно используется deterministic fallback. Unauthorized tool use должен отклоняться и
логироваться как security event.

## Hard stops

Demo/live hard stops относятся к future scope, но research code уже должен моделировать
safety thinking. Примеры hard stops: max drawdown breach, repeated execution errors, stale
data, unexpected exposure и runaway order generation.

Research workflows должны отправлять affected experiments в quarantine и требовать human
review после critical failures.

## Testing strategy

Codebase должен сохранять быстрый unit baseline для обычных commits. Property tests
рекомендуются для statistical и data-quality invariants: timestamp normalization, missing
bar detection, duplicate detection, outlier sensitivity, resampling idempotence, timestamp
alignment, cointegration accuracy, ADF detection, half-life estimation, z-score properties,
PnL conservation, turnover consistency, risk compliance и reproducibility.

LLM и OmniRoute checks должны оставаться отдельно от обычного pre-commit check, потому что
они зависят от external service state.

## MVP acceptance

MVP завершен, когда проект умеет initialize repository и local infrastructure, ingest и
validate хотя бы один data source, запускать хотя бы один scripted pair-screening workflow,
выполнять statistical testing и backtesting workflows, писать structured records в
registry, писать concise summaries в LightRAG, показывать experiments через dashboard или
report view и проходить CI.

Non-functional acceptance включает поддержку local PC, Oracle Cloud Always Free
compatibility, reasonable memory and disk usage, отсутствие paid data dependency в v1,
Infisical-managed secrets и full experiment runtime target, пригодный для iterative
research.

## Источники

- `.kiro/specs/quant-research-architecture/requirements.md`
- `.kiro/specs/quant-research-architecture/design.md`
- `.kiro/specs/quant-research-architecture/tasks.md`
