# Контракты памяти агентов

Этот shard определяет, что каждый агент должен записывать в LightRAG, а что должно
оставаться в structured registry. Материал подготовлен из Kiro requirements и design docs.

## Общее правило

LightRAG хранит высокоуровневую память: обоснования, уроки, решения, краткие выводы,
связи, ручные заметки и ссылки на код. В LightRAG нельзя хранить raw logs, raw prompts,
секреты, большие datasets, OHLCV-данные и точные числовые метрики, которые должны жить в
structured registry.

Structured registry является source of truth для experiment IDs, dataset IDs, параметров,
p-values, test statistics, hedge ratios, backtest metrics, costs, artifacts, review states и
final decisions.

## Coordinator Agent

Coordinator Agent управляет очередью задач и lifecycle эксперимента. Он записывает в
LightRAG события lifecycle, final decisions, причины отклонения, причины promotion и ссылки
на registry. Статус эксперимента и метрики он читает из registry.

Ожидаемый lifecycle:

```text
NEW -> DATA_VALIDATION -> STATISTICAL_TESTING -> BACKTESTING -> CRITIC_REVIEW -> REPORTING -> FINAL_DECISION
```

## Data Agent

Data Agent загружает OHLCV-данные, проверяет качество, пишет datasets в Parquet, а dataset
IDs и quality reports записывает в registry. Ошибки валидации и quarantine decisions он
пишет в LightRAG.

Data quality validation должна покрывать нормализацию timestamps в UTC, duplicate
timestamps, missing bars, impossible candles, abnormal volume spikes, deterministic
resampling, pair alignment, provenance и quality thresholds.

## Hypothesis Agent

Hypothesis Agent читает рыночные знания и прошлые hypotheses из LightRAG, проверяет
отклоненные пары в registry, генерирует candidate pairs с rationale и записывает hypotheses
и в LightRAG, и в registry.

Он должен связывать похожие hypotheses в LightRAG и помечать retests ранее отклоненных идей.
LLM-generated hypotheses требуют critic review и budget limits.

## Statistical Testing Agent

Statistical Testing Agent требует validated datasets до запуска тестов. Он пишет structured
p-values, test statistics, hedge ratios и связанные метрики в registry. В LightRAG он
записывает краткие уроки и интерпретацию результата.

## Backtest Agent

Backtest Agent пишет structured performance metrics, gross PnL, net PnL, turnover, cost
attribution и artifact references в registry. В LightRAG он записывает краткие conclusions,
lessons learned и regime observations.

## Critic Agent

Critic Agent проверяет leakage risk, overfitting, weak assumptions, insufficient testing,
unrealistic costs и качество решения. Он записывает objections, detected risks, review
status и recommendations в LightRAG и registry.

## Report Agent

Report Agent пишет ссылки на report artifacts и structured report metadata в registry. В
LightRAG он записывает human-readable summaries и manual review notes.

## Memory Agent

Memory Agent владеет операциями чтения и записи LightRAG. Он читает registry records ради
IDs и ссылок, но не пишет строки в registry. Он поддерживает topic, entity и relationship
queries для других агентов.

## Источники

- `.kiro/specs/quant-research-architecture/requirements.md`
- `.kiro/specs/quant-research-architecture/design.md`
