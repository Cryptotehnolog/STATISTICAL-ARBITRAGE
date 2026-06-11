# Statistical Arbitrage: мультиагентная платформа quantitative research

Воспроизводимая исследовательская платформа для statistical arbitrage и pairs trading: генерация гипотез, строгая statistical validation, backtesting с подробным учетом costs и долгосрочная память через ApeRAG.

## Обзор проекта

Система строится как поэтапная платформа для quantitative research:

- **v1 (текущий этап)**: research platform с контролем качества данных, statistical validation и cost modeling.
- **v2 (будущий этап)**: demo trading через paper accounts и risk management.
- **v3 (будущий этап)**: ограниченный live trading со строгими approval gates.

Ключевые возможности:

- Multi-agent architecture для data, hypothesis generation, statistical testing, backtesting и review.
- Долгосрочная память и knowledge graph через ApeRAG.
- Строгая data quality validation: timezone normalization, missing bars, outliers, alignment.
- Statistical testing: Engle-Granger cointegration, ADF tests, hedge ratio estimation.
- Walk-forward backtesting с подробным cost attribution.
- Автоматический critic review на lookahead bias, overfitting и weak assumptions.
- Интерактивный dashboard для мониторинга experiments и просмотра reports.

## Архитектура

### Принципы проектирования

1. **Корректность важнее скорости**: приоритет у reproducibility, data quality и statistical rigor.
2. **Ограниченные ресурсы**: работа на локальном ПК и Oracle Cloud Always Free ARM.
3. **Пошаговое усложнение**: сначала research, затем demo trading, затем ограниченный live trading.
4. **Память с первого дня**: ApeRAG хранит долгосрочную память, knowledge search и graph.
5. **Human in the loop**: критичные решения проходят через approval gates.
6. **Python-first, Rust только по профилированию**: Rust добавляется только там, где Python реально стал узким местом.
7. **Минимальная инфраструктура для v1**: SQLite и Parquet локально; ApeRAG, Infisical и OmniRoute как Docker-supported runtime.

### Agent architecture

```text
User Interface
Dashboard (Streamlit) + CLI Tools
        |
Coordinator Agent
Task Queue & Experiment Lifecycle
        |
Data Agent | Hypothesis Agent | Statistical Testing Agent
        |
Backtest Agent | Critic Agent | Report Agent
        |
Memory Agent
ApeRAG Operations
        |
ApeRAG (Memory) | SQLite (Registry) | Parquet (Data)
```

### Жизненный цикл experiment

```text
NEW -> DATA_VALIDATION -> STATISTICAL_TESTING -> BACKTESTING ->
CRITIC_REVIEW -> REPORTING -> FINAL_DECISION
```

Финальные решения:

- **Reject**: найдены критичные проблемы, например lookahead bias, negative net PnL или insufficient testing.
- **Quarantine**: найдены умеренные проблемы, например weak statistics, high turnover или borderline costs.
- **Approve**: критичных проблем нет, можно передать на human review.

## Быстрый старт

### Требования

- **Python**: 3.11 или новее.
- **uv**: менеджер зависимостей Python ([инструкция по установке](https://github.com/astral-sh/uv)).
- **Hardware**: минимум 8 GB RAM и 20 GB свободного места.
- **OS**: Windows, Linux или macOS.

### Установка

1. Клонировать repository:

   ```bash
   git clone https://github.com/Cryptotehnolog/STATISTICAL-ARBITRAGE.git
   cd STATISTICAL-ARBITRAGE
   ```

2. Установить зависимости через `uv`:

   ```bash
   uv sync
   ```

3. Настроить environment variables:

   ```bash
   cp .env.example .env
   # Отредактируйте .env под локальную конфигурацию
   ```

4. Поднять локальный Infisical для secrets management:

   ```powershell
   .\scripts\init_infisical_env.ps1
   .\scripts\start_infisical.ps1
   .\scripts\check_infisical.ps1
   ```

   UI будет доступен на `http://localhost:8080`. Первый зарегистрированный пользователь
   становится administrator локального instance. После создания project и machine identity
   добавьте runtime credentials в `.env`:

     ```text
     INFISICAL_API_URL=http://localhost:8080
     INFISICAL_CLIENT_ID=your_client_id
     INFISICAL_CLIENT_SECRET=your_client_secret
     INFISICAL_PROJECT_ID=your_project_id
     ```

   Затем создайте test secret `STAT_ARB_INFISICAL_SMOKE_SECRET` и проверьте runtime access:

   ```powershell
   .\scripts\check_infisical_auth.ps1
   ```

5. Инициализировать database:

   ```bash
   uv run python -m stat_arb.scripts.init_database
   ```

6. Поднять ApeRAG как active memory backend:

   ```powershell
   .\scripts\start_aperag_embedding_server.ps1
   .\scripts\start_aperag.ps1
   .\scripts\configure_aperag.ps1
   ```

7. Наполнить curated project memory и проверить backend:

   ```powershell
   .\scripts\seed_aperag_curated.ps1 -Force -EnableGraph
   .\scripts\enable_aperag_curated_graph.ps1
   .\scripts\check_memory_backend.ps1 -RequireGraph
   .\scripts\check_aperag_agent_memory.ps1
   ```

### Команды ApeRAG и OmniRoute

Проверить ApeRAG containers, API, embedding endpoint и optional graph smoke:

```powershell
.\scripts\check_aperag.ps1
```

Проверить, что project memory синхронизирована и отвечает на search:

```powershell
.\scripts\check_aperag_memory_fresh.ps1 -RequireGraph
```

Проверить active memory backend без legacy memory path:

```powershell
.\scripts\check_memory_backend.ps1 -RequireGraph
```

Проверить отдельную operational agent memory collection:

```powershell
.\scripts\check_aperag_agent_memory.ps1
```

Проверить deterministic Memory Agent contracts без зависимости от внешней LLM/ApeRAG runtime:

```powershell
.\scripts\check_memory_agent_pipeline.ps1
```

При необходимости добавить runtime smoke для ApeRAG:

```powershell
.\scripts\check_memory_agent_pipeline.ps1 -IncludeRuntimeHealth
```

Проверить OmniRoute container, API и короткий chat route:

```powershell
.\scripts\check_omniroute.ps1
```

Локальный pre-commit checklist без LLM-зависимостей:

```powershell
.\scripts\pre_commit_check.ps1
```

Проверить, что secrets не попали в tracked files, а локальные runtime `.env` остаются ignored:

```powershell
.\scripts\check_secret_leaks.ps1
```

Более тяжелая проверка Git history:

```powershell
.\scripts\check_secret_leaks.ps1 -IncludeGitHistory
```

Показать regenerable runtime/cache artifacts для безопасной чистки:

```powershell
.\scripts\clean_runtime_artifacts.ps1
```

Удалить найденные runtime/cache artifacts:

```powershell
.\scripts\clean_runtime_artifacts.ps1 -Apply
```

Проверить, что user-facing labels и messages остаются русифицированными:

```powershell
.\scripts\check_user_facing_russian.ps1
```

Найти большие markdown-файлы и секции-кандидаты для curated memory shards:

```powershell
.\scripts\suggest_knowledge_shards.ps1
```

## Запуск системы

Запустить dashboard:

```bash
uv run streamlit run src/stat_arb/dashboard/app.py
```

CLI examples:

```bash
# Скачать OHLCV, проверить качество и сохранить registry records
uv run stat-arb data download --exchange binance --symbol BTC/USDT --timeframe 15m --since 2024-01-01T00:00:00+00:00 --limit 500 --raw-output-root data/raw --metadata-root data/registry --db-path data/registry.db --max-missing-bar-ratio 0 --max-abnormal-volume-ratio 0 --volume-spike-multiplier 10

# Проверить OHLCV sample без записи в registry
uv run stat-arb data validate --exchange binance --symbol BTC/USDT --timeframe 15m --since 2024-01-01T00:00:00+00:00 --limit 500 --max-missing-bar-ratio 0 --max-abnormal-volume-ratio 0 --volume-spike-multiplier 10

# Показать сохраненные datasets
uv run stat-arb data list --db-path data/registry.db

# Добавить manual hypothesis
uv run stat-arb hypothesis add --asset-a BTC/USDT --asset-b ETH/USDT --rationale "Manual crypto spread candidate" --source user_provided --created-by operator --novelty-score 1.0 --status new --db-path data/registry.db

# Показать hypotheses
uv run stat-arb hypothesis list --db-path data/registry.db

# Сгенерировать rule-based hypotheses из JSON universe/contracts
uv run stat-arb hypothesis generate --assets-json data/research/assets.json --correlations-json data/research/correlations.json --p-values-json data/research/p_values.json --require-same-sector --min-abs-correlation 0.85 --min-market-cap 50000000000 --max-market-cap 150000000000 --max-pairs 10 --multiple-testing-method bonferroni --candidate-alpha 0.05 --initial-novelty-score 1.0 --initial-status new --source rule_based --created-by hypothesis_agent --db-path data/registry.db

# Показать experiments
uv run stat-arb experiment list --db-path data/registry.db

# Показать статус одного experiment
uv run stat-arb experiment status --experiment-id <uuid> --db-path data/registry.db

# Перевести experiment в следующий lifecycle status через Coordinator boundary
uv run stat-arb experiment advance --experiment-id <uuid> --target-status data_validation --reason "Operator starts validated data stage." --actor cli_operator --db-path data/registry.db

# Поставить stage task в Coordinator queue с явными retry/priority/payload
uv run stat-arb experiment run-stage --experiment-id <uuid> --stage statistical_testing --task-type run_statistical_tests --agent-name statistical_testing_agent --priority 2 --max-attempts 3 --payload-json data/research/statistical_stage_payload.json --advance-lifecycle --reason "Queue statistical testing after data validation." --actor cli_operator --db-path data/registry.db

# Выполнить queued statistical_testing stage через локальный agent service
uv run stat-arb experiment execute-stage --task-id <uuid> --stage statistical_testing --max-running-tasks 1 --max-running-tasks-per-agent 1 --db-path data/registry.db
```

## Источники данных

### Cryptocurrency

- **CCXT Library**: поддержка нескольких exchanges, включая Binance, Coinbase Pro и Kraken.
- **Плюсы**: бесплатно, надежно, хорошее intraday coverage.
- **Ограничения**: rate limits зависят от exchange.
- **Intraday availability**: от 1-minute до 1-hour bars.
- **Historical depth**: обычно 1-2 года для minute data.

### US Equities

- **Alpaca API**: есть free tier.
- **Плюсы**: качественные intraday data.
- **Ограничения**: только US stocks, rate limits на free tier.
- **Intraday availability**: от 1-minute до 1-hour bars.
- **Historical depth**: ограничен на free tier.

Yahoo Finance не рекомендуется для intraday data из-за gaps и нестабильности.

## Тестирование

Запустить все tests:

```bash
uv run pytest
```

Запустить tests с coverage:

```bash
uv run pytest --cov=stat_arb --cov-report=html
```

Property-based tests:

```bash
uv run pytest -m property
```

Категории tests:

```bash
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m "not slow"
```

## Разработка

Linting и formatting:

```bash
uv run ruff check .
uv run ruff format .
```

Type checking:

```bash
uv run mypy src/stat_arb
```

Pre-commit checks:

```bash
uv run pytest && uv run ruff check . && uv run mypy src/stat_arb
```

## Структура repository

```text
.
├── src/stat_arb/           # Основной package code
│   ├── agents/             # Agent implementations
│   ├── models/             # Pydantic data models
│   ├── storage/            # Database interfaces
│   ├── data/               # Data ingestion и validation
│   ├── statistical/        # Statistical testing functions
│   ├── backtest/           # Backtesting engine
│   ├── dashboard/          # Streamlit dashboard
│   ├── cli/                # CLI commands
│   └── utils/              # Shared utilities
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── property/           # Property-based tests
├── data/                   # Runtime data, ignored by Git
│   ├── parquet/            # OHLCV data
│   └── aperag/             # ApeRAG runtime config и manifests
├── docs/                   # Документация
├── scripts/                # Utility scripts
├── .github/                # GitHub Actions CI/CD
├── pyproject.toml          # Project configuration
├── .env.example            # Environment variables template
└── README.md               # Этот файл
```

## Security и secrets management

Все secrets должны храниться через Infisical:

- API keys для exchanges: Binance, Coinbase, Kraken, Alpaca.
- Database passwords, если будет PostgreSQL.
- LLM API keys.
- Webhook tokens и Telegram bot tokens.

Локальный self-host Infisical запускается отдельным Docker stack:

```powershell
.\scripts\init_infisical_env.ps1
.\scripts\start_infisical.ps1
.\scripts\check_infisical.ps1
.\scripts\check_infisical_auth.ps1
```

Сервис открывается только на `127.0.0.1:8080`; PostgreSQL и Redis не публикуются наружу.
Файл `infra/infisical/.env` содержит bootstrap keys для шифрования Infisical. Не удаляйте
его без backup, иначе восстановить secrets из Docker volume будет нельзя.

`check_infisical_auth.ps1` проверяет Universal Auth и чтение test secret
`STAT_ARB_INFISICAL_SMOKE_SECRET`. Значение secret не выводится в консоль.

Нельзя коммитить secrets в Git:

- `.env` находится в `.gitignore`.
- `infra/infisical/.env` находится в `.gitignore`.
- `.env.example` используется только как документация.
- Secrets загружаются из Infisical во время runtime.

## Hardware requirements

### Local development

- **CPU**: Intel i5 или аналог.
- **RAM**: минимум 8 GB, рекомендуется 16 GB+.
- **Disk**: минимум 20 GB.
- **Network**: обычный стабильный internet.

### Рекомендуемая конфигурация

- **CPU**: Intel i5-1335U или лучше.
- **RAM**: 32 GB.
- **Disk**: 100 GB SSD.
- **Network**: стабильное подключение для data ingestion.

### Oracle Cloud Always Free

- **CPU**: 4 vCPU ARM.
- **RAM**: 24 GB.
- **Disk**: 200 GB.
- **Cost**: free tier.

## Примеры workflow

Скачать cryptocurrency data:

```bash
uv run stat-arb data download \
  --exchange binance \
  --symbol BTC/USDT \
  --timeframe 15m \
  --since 2024-07-01T00:00:00+00:00 \
  --limit 500 \
  --raw-output-root data/raw \
  --metadata-root data/registry \
  --db-path data/registry.db \
  --max-missing-bar-ratio 0 \
  --max-abnormal-volume-ratio 0 \
  --volume-spike-multiplier 10
```

Сгенерировать candidate pairs из подготовленных JSON contracts:

```bash
uv run stat-arb hypothesis generate \
  --assets-json data/research/assets.json \
  --correlations-json data/research/correlations.json \
  --p-values-json data/research/p_values.json \
  --require-same-sector \
  --min-abs-correlation 0.85 \
  --min-market-cap 50000000000 \
  --max-market-cap 150000000000 \
  --max-pairs 20 \
  --multiple-testing-method bonferroni \
  --candidate-alpha 0.05 \
  --initial-novelty-score 1.0 \
  --initial-status new \
  --source rule_based \
  --created-by hypothesis_agent \
  --db-path data/registry.db
```

Проверить lifecycle status:

```bash
uv run stat-arb experiment status \
  --experiment-id <uuid> \
  --db-path data/registry.db
```

Перевести experiment в следующий lifecycle status:

```bash
uv run stat-arb experiment advance \
  --experiment-id <uuid> \
  --target-status data_validation \
  --reason "Operator starts validated data stage." \
  --actor cli_operator \
  --db-path data/registry.db
```

Поставить stage task в Coordinator queue:

```bash
uv run stat-arb experiment run-stage \
  --experiment-id <uuid> \
  --stage statistical_testing \
  --task-type run_statistical_tests \
  --agent-name statistical_testing_agent \
  --priority 2 \
  --max-attempts 3 \
  --payload-json data/research/statistical_stage_payload.json \
  --advance-lifecycle \
  --reason "Queue statistical testing after data validation." \
  --actor cli_operator \
  --db-path data/registry.db
```

Выполнить queued `statistical_testing` stage:

```bash
uv run stat-arb experiment execute-stage \
  --task-id <uuid> \
  --stage statistical_testing \
  --max-running-tasks 1 \
  --max-running-tasks-per-agent 1 \
  --db-path data/registry.db
```

Dashboard:

```bash
uv run streamlit run src/stat_arb/dashboard/app.py
```

## Документация

- **Architecture**: `docs/architecture.md`.
- **Agent roles**: `docs/agents.md`.
- **Data architecture**: `docs/data.md`.
- **API reference**: `docs/api.md`.
- **Database schema**: `docs/schema.md`.

## Юридические предупреждения

Система является research tool, а не financial advice:

- Нет гарантий прибыльности или performance.
- Past performance does not indicate future results.
- Использование на свой риск.

Exchange terms of service:

- Соблюдайте terms of service каждого exchange.
- Уважайте rate limits и API usage policies.
- Проверяйте licensing для data usage.

Audit logs:

- Все agent decisions проходят через Memory Agent policy layer и пишутся в ApeRAG.
- Все experiments отслеживаются в SQLite registry.
- Audit trails нужны для compliance.

## Roadmap

### v1: Research Platform

- Data ingestion с quality validation.
- Hypothesis generation и novelty checking.
- Statistical testing: cointegration, ADF, hedge ratio.
- Walk-forward backtesting с cost attribution.
- Critic review на bias и overfitting.
- ApeRAG memory, search и knowledge graph.
- Dashboard и CLI tools.

### v2: Demo Trading

- Paper trading с simulated execution.
- Risk management и position sizing.
- Real-time data feeds.
- Kill switch и emergency stop.
- Human approval gates.

### v3: Limited Live Trading

- Live execution со строгими risk limits.
- Advanced monitoring и alerting.
- Multi-strategy portfolio management.
- Performance attribution и reporting.

## Contributing

Contributions welcome:

1. Fork repository.
2. Создайте feature branch.
3. Добавьте tests для новой функциональности.
4. Убедитесь, что tests проходят: `uv run pytest`.
5. Запустите linting: `uv run ruff check .`.
6. Создайте pull request.

## License

MIT License, см. `LICENSE`.

## Acknowledgments

- **ApeRAG**: long-term memory, search и knowledge graph framework.
- **CCXT**: unified cryptocurrency exchange API.
- **Statsmodels**: statistical testing и econometrics.
- **Streamlit**: interactive dashboard framework.

## Контакты

- **GitHub**: [Cryptotehnolog](https://github.com/Cryptotehnolog)
- **Repository**: [STATISTICAL-ARBITRAGE](https://github.com/Cryptotehnolog/STATISTICAL-ARBITRAGE)
- **Issues**: [bugs и feature requests](https://github.com/Cryptotehnolog/STATISTICAL-ARBITRAGE/issues)
