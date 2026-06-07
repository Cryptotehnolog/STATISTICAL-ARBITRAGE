# Checkpoint-аудит Tasks 8-10

Дата: 2026-06-07

Область проверки:
- Проверить, что реализованные statistical testing и backtest закрывают checkpoint task 8.
- Проверить, есть ли у tasks 9-10 реальная реализация или только planning/storage scaffold.
- Найти boundary risks перед началом Hypothesis Agent и Critic Agent.

## Доказательства

- `scripts/check_statistical_pipeline.ps1` запускает tests для statistical functions и boundary tests для Statistical Testing Agent.
- `scripts/check_backtest_pipeline.ps1` запускает tests для core backtest, costs, metrics, baseline, sensitivity, reproducibility, walk-forward и Backtest Agent boundary.
- `scripts/check_memory_health.ps1` проверяет active ApeRAG project memory, graph readiness и operational agent memory smoke.
- `src/stat_arb/agents/` сейчас содержит только `statistical_testing.py` и `backtest.py`.
- Файлов реализации Hypothesis Agent и Critic Agent пока нет.

## Выводы

- Task 8 можно закрывать после прохода executable checkpoint checks.
- Tasks 9 и 10 должны остаться открытыми. Registry models для `Hypothesis` и `CriticReview` есть, но это storage scaffold, а не agent implementation.
- Batch hypothesis screening не должен незаметно использовать uncorrected p-values. Candidate batches требуют explicit multiple-testing correction перед approval или persistence.
- Будущие Hypothesis Agent и Critic Agent writes должны идти через SQLite registry и Memory Agent policy boundary, а не напрямую в ApeRAG.
- Critic Agent thresholds должны оставаться explicit policy configuration, а не hidden defaults.

## Рекомендация

Переходить к task 9 стоит только после green checkpoint commit. Начинать лучше с маленького Hypothesis Agent boundary и tests, а не с широкого multi-agent workflow.
