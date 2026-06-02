# MVP scope и ограничения

Этот shard кратко фиксирует долговечные scope rules из Kiro architecture specs. Он
предназначен для LightRAG seeding и должен оставаться меньше исходных design documents.

## V1 scope

Система v1 является воспроизводимой research platform для statistical arbitrage, а не live
trading system. Она должна поддерживать hypothesis generation, statistical validation,
reproducible backtesting, cost attribution, critic review, reporting, structured experiment
storage и long-term memory.

V1 фокусируется только на pairs trading. Основной timeframe — 15-minute bars; 5-minute bars
являются secondary после валидации pipeline. One-minute bars, demo trading, live trading,
streaming infrastructure, enterprise monitoring и multi-strategy portfolio allocation не
входят в первый MVP.

## Hardware constraints

Система должна работать на локальном Intel i5-1335U PC с 32 GB RAM и без CUDA GPU. Она также
должна оставаться compatible с Oracle Cloud Always Free ARM resources. Local development
должен предпочитать простые компоненты, которым не нужна тяжелая always-on infrastructure.

## Infrastructure rules

Local MVP должен работать с Python, uv, SQLite, Parquet и embedded LightRAG/vector storage.
Docker разрешен для optional supporting tools и production-like testing, но он не должен
блокировать обычную local development или pre-commit checks.

SQLite или другой простой structured registry должен быть source of truth для numeric
metrics, experiment IDs, dataset IDs, parameters, costs и final decisions. LightRAG
используется для summaries, rationale, relationships, lessons learned и development memory.

## Implementation bias

Предпочитать correctness, auditability и reproducibility, а не скорость. Начинать с Python
reference implementations. Rust добавлять только там, где profiling доказывает
performance-critical bottleneck, а API boundary уже стабилен.

## Источники

- `.kiro/specs/quant-research-architecture/requirements.md`
- `.kiro/specs/quant-research-architecture/design.md`
