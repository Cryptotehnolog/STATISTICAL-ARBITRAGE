# Rust strategy

Проект остается Python-first для MVP, но Rust является целевым языком для будущего
производительного ядра. Это не противоречие: Python отвечает за orchestration, agents,
research workflow, dashboard, API integrations и RAG; Rust подключается там, где profiling
покажет устойчивый hot path.

## Почему не начинать с Rust core сразу

На раннем этапе еще меняются data contracts, registry schema, statistical assumptions и
backtest semantics. Если перенести ядро в Rust до стабилизации этих границ, проект получит
более дорогие изменения, более сложную сборку и больше FFI/packaging работы без
доказанного выигрыша.

## Где Rust вероятнее всего нужен

- Resampling и alignment больших OHLCV datasets.
- Rolling statistics, z-score construction и pair screening на большом числе pairs.
- Backtest loop, position accounting и cost attribution, если Python reference окажется
  узким местом.
- Simulation-heavy property tests и synthetic data generation.
- Будущий execution/risk core, если проект дойдет до demo/live trading.

## Условия переноса модуля в Rust

Модуль можно переносить в Rust только когда выполнены все условия:

- Есть Python reference implementation с unit/property tests.
- API boundary стабилен и описан в Python/Pydantic или typed data structures.
- Profiling показывает, что модуль является реальным bottleneck.
- Есть benchmark до и после переноса.
- Rust package не ломает обычный Python developer workflow.

## Рекомендуемая integration model

Для Python MVP предпочтителен `maturin` + `pyo3` как optional acceleration package. Python
остается владельцем orchestration и domain workflow, Rust предоставляет чистые функции для
hot-path computations. До появления первого Rust модуля optional dependency `rust` в
`pyproject.toml` достаточно.

## Не делать

- Не переносить agents, dashboard, CLI и RAG integration в Rust.
- Не добавлять Rust ради процента языка в GitHub.
- Не писать unsafe code без отдельного review и documented safety invariants.
- Не вводить Rust build step в default `scripts/check.ps1`, пока Rust остается optional.
