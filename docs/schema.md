# Structured Registry schema

Structured Registry является source of truth для структурированных experiment records и
numeric metrics. Текущая локальная реализация использует SQLite через SQLAlchemy models.

## Ownership

- Registry хранит exact records.
- ApeRAG хранит searchable summaries и registry references.
- ApeRAG не хранит raw metrics как source of truth и не заменяет registry.

## Основные группы записей

- `datasets`: source, symbol, timeframe, storage path, provenance, validation status.
- `data_quality_reports`: missing bars, duplicate timestamps, outliers, alignment status,
  validity flags и failure reasons.
- `hypotheses`: assets, rationale, source, novelty score, status и related hypotheses.
- `experiments`: lifecycle state, current stage, decisions, actor/reason provenance.
- `statistical_results`: cointegration, ADF, hedge ratio, half-life, z-score diagnostics
  and policy metadata.
- `backtest` records: PnL, costs, metrics, baselines, sensitivity, reproducibility hashes
  and artifact references.
- `reports`: generated report paths, factual sidecar links and summary metadata.

## Reproducibility

Backtest and experiment records must include enough metadata to rerun or explain the run:
git commit, lockfile hash, config hash, dataset IDs, random seed where applicable, command
and timestamp.

## Migration policy

SQLite is sufficient for local v1. Postgres can be introduced later only behind the same
Structured Registry boundary when concurrency or deployment needs justify it.
