# Архитектура проекта

Этот документ описывает текущее состояние v1 research platform, а не будущую live trading
систему. Проект не является live trading системой и не должен обещать production-ready
торговлю реальными деньгами.

## Текущая v1 архитектура

- Python-first: orchestration, agents, CLI, dashboard, RAG/memory и research workflows
  реализуются на Python.
- Rust остается optimization path: Rust добавляется только после profiler output,
  стабильного Python reference и понятной API boundary.
- Structured Registry использует SQLite как локальный источник структурированных записей.
- Market data и artifacts хранятся как Parquet/JSON sidecars.
- ApeRAG является active long-term memory backend и knowledge graph.
- Memory Agent policy является обязательной границей: агенты не пишут напрямую в ApeRAG.
- Infisical используется для secrets management.
- OmniRoute является primary LLM gateway для ApeRAG graph rebuild, а FreeDeepseekAPI и
  FreeQwenApi остаются explicit fallback providers.

## Storage ownership

SQLite Structured Registry хранит точные numeric records: datasets, quality reports,
hypotheses, statistical results, backtest metrics, reproducibility metadata, reports и
final decisions. ApeRAG хранит searchable summaries, decisions, lessons и registry
references. ApeRAG не должен становиться источником точных метрик.

## Runtime boundaries

Обычные deterministic checks не зависят от Docker, LLM providers, Infisical auth или
ApeRAG graph rebuild. Runtime readiness проверяется отдельными командами: memory checks,
Infisical checks, OmniRoute readiness и ApeRAG graph checks.

## Staged scope

v1 фокусируется на reproducible research: ingestion, validation, pair screening,
statistical testing, backtesting, critic review, reporting, dashboard inspection и CLI.
Paper/live trading, autonomous capital allocation, execution gateways и dynamic risk agents
отложены до отдельных staged decisions.
