# Примеры workflows

Эти examples показывают реальные entrypoints проекта. Этот слой не является full autonomous experiment runner: каждая команда идет через уже реализованные boundaries, пишет в
Structured Registry и не обходит Coordinator, Memory Agent policy или report guards.

Перед запуском examples используйте локальный registry path и JSON payloads, подготовленные
для вашего эксперимента. Значения thresholds, costs, metric assumptions и windows должны
быть явными и проверенными; не переносите демонстрационные числа в research без approval.

## 1. Ingest crypto data from Bybit

Bybit является стартовым crypto venue. Live exchange access остается opt-in, поэтому этот
пример не входит в `pre-commit`.

```powershell
uv run stat-arb data download `
  --exchange bybit `
  --symbol BTC/USDT `
  --timeframe 15m `
  --since 2024-01-01T00:00:00+00:00 `
  --limit 500 `
  --raw-output-root data/raw `
  --metadata-root data/registry `
  --db-path data/registry.db `
  --max-missing-bar-ratio 0 `
  --max-abnormal-volume-ratio 0 `
  --volume-spike-multiplier 10
```

Что должно появиться: Parquet partitions, registry `datasets` row и
`data_quality_reports` row. Если quality validation не проходит, pipeline должен
остановиться до downstream statistical testing.

## 2. Screen pairs by sector/correlation

Pair screening идет через Hypothesis Agent boundary и не пишет hypotheses напрямую в
database tables.

```powershell
.\scripts\screen_pairs.ps1 `
  -AssetsJson examples/assets.json `
  -CorrelationsJson examples/correlations.json `
  -PValuesJson examples/p_values.json `
  -RequireSameSector `
  -MinAbsCorrelation 0.80 `
  -MinMarketCap 1000000000 `
  -MaxPairs 10 `
  -MultipleTestingMethod benjamini_hochberg `
  -CandidateAlpha 0.05 `
  -InitialNoveltyScore 0.50 `
  -InitialStatus candidate `
  -Source manual_screening `
  -CreatedBy researcher `
  -DbPath data/registry.db
```

Внутри wrapper вызывает реальный CLI entrypoint:

```powershell
uv run stat-arb hypothesis generate --assets-json examples/assets.json --correlations-json examples/correlations.json --p-values-json examples/p_values.json --min-abs-correlation 0.80 --min-market-cap 1000000000 --max-pairs 10 --multiple-testing-method benjamini_hochberg --candidate-alpha 0.05 --initial-novelty-score 0.50 --initial-status candidate --source manual_screening --created-by researcher --db-path data/registry.db
```

## 3. Run statistical tests on a pair

Statistical testing должен идти через Coordinator task queue. Workflow сначала ставит
stage task, затем исполняет его через `execute-stage`.

```powershell
.\scripts\run_statistical_testing.ps1 `
  -ExperimentId <experiment-id> `
  -PayloadJson examples/statistical_testing_payload.json `
  -Priority 10 `
  -MaxAttempts 1 `
  -Reason "run statistical testing" `
  -Actor researcher `
  -MaxRunningTasks 1 `
  -MaxRunningTasksPerAgent 1 `
  -DbPath data/registry.db
```

Ключевые CLI boundaries:

```powershell
uv run stat-arb experiment run-stage --experiment-id <experiment-id> --stage statistical_testing --task-type run_statistical_tests --agent-name statistical_testing_agent --priority 10 --max-attempts 1 --payload-json examples/statistical_testing_payload.json --advance-lifecycle --reason "run statistical testing" --actor researcher --db-path data/registry.db
uv run stat-arb experiment execute-stage --task-id <task-id> --stage statistical_testing --max-running-tasks 1 --max-running-tasks-per-agent 1 --db-path data/registry.db
```

## 4. Run backtest and guarded reporting

Backtest workflow пишет structured result, reproducibility metadata и factual
`backtest_series` sidecar. Reporting допускается только как guarded reporting: Report Agent
может строить графики только если registry содержит matching `backtest_series` artifact.

```powershell
.\scripts\run_backtest.ps1 `
  -ExperimentId <experiment-id> `
  -PayloadJson examples/backtest_payload.json `
  -Priority 10 `
  -MaxAttempts 1 `
  -Reason "run backtest" `
  -Actor researcher `
  -MaxRunningTasks 1 `
  -MaxRunningTasksPerAgent 1 `
  -DbPath data/registry.db
```

Если уже есть pending backtesting task и payload содержит factual series, можно запускать
узкий artifact-gated pipeline:

```powershell
uv run stat-arb experiment run-pipeline --experiment-id <experiment-id> --stages backtesting,reporting --backtesting-task-id <task-id> --report-output-dir reports/local --max-running-tasks 1 --max-running-tasks-per-agent 1 --db-path data/registry.db
```

## 5. Проверить examples как guard

```powershell
.\scripts\check_cli_scripted_workflows.ps1
```

Эта проверка прогоняет mock-data цепочку
`screen_pairs.ps1` -> `run_statistical_testing.ps1` -> `run_backtest.ps1` -> guarded
reporting execution. Она доказывает, что examples опираются на реальные workflows, а не на
несуществующие команды.
