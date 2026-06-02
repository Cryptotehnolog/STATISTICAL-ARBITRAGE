# Statistical Arbitrage: мультиагентная платформа quantitative research

Воспроизводимая исследовательская платформа для statistical arbitrage и pairs trading: генерация гипотез, строгая statistical validation, backtesting с подробным учетом costs и долгосрочная память через LightRAG.

## Обзор проекта

Система строится как поэтапная платформа для quantitative research:

- **v1 (текущий этап)**: research platform с контролем качества данных, statistical validation и cost modeling.
- **v2 (будущий этап)**: demo trading через paper accounts и risk management.
- **v3 (будущий этап)**: ограниченный live trading со строгими approval gates.

Ключевые возможности:

- Multi-agent architecture для data, hypothesis generation, statistical testing, backtesting и review.
- Долгосрочная память и knowledge graph через LightRAG.
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
4. **Память с первого дня**: LightRAG хранит долгосрочную память и knowledge graph.
5. **Human in the loop**: критичные решения проходят через approval gates.
6. **Python-first, Rust только по профилированию**: Rust добавляется только там, где Python реально стал узким местом.
7. **Минимальная инфраструктура для v1**: SQLite + embedded vector store (FAISS/NanoVectorDB).

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
LightRAG Operations
        |
LightRAG (Memory) | SQLite (Registry) | Parquet (Data)
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

6. Инициализировать LightRAG:

   ```bash
   uv run python -m stat_arb.scripts.init_lightrag
   ```

   Более тяжелая локальная проверка с загрузкой embedding model и insert/query smoke test:

   ```bash
   uv run python -m stat_arb.scripts.init_lightrag --smoke-test
   ```

### Команды LightRAG и OmniRoute

Наполнить LightRAG проектными знаниями из README, docs и `.kiro/specs`:

```bash
.\scripts\seed_lightrag.ps1
```

На первом запуске машины разрешить разовую загрузку embedding model:

```bash
.\scripts\seed_lightrag.ps1 --allow-model-download
```

Включить entity/relation extraction через OpenAI-compatible gateway:

```bash
.\scripts\seed_lightrag.ps1 --llm-provider openai_compatible --openai-compatible-model my-ai
```

Preview ограниченного OmniRoute seed без записи:

```bash
.\scripts\seed_lightrag_omniroute.ps1
```

Применить ограниченный OmniRoute seed:

```bash
.\scripts\seed_lightrag_omniroute.ps1 -Apply
```

Preview или apply только curated shards из `docs/knowledge`:

```bash
.\scripts\seed_lightrag_curated.ps1
.\scripts\seed_lightrag_curated.ps1 -Apply
```

Smoke-test graph extraction через OmniRoute:

```bash
.\scripts\smoke_lightrag_omniroute.ps1
```

Benchmark порядка моделей OmniRoute для LightRAG extraction:

```bash
.\scripts\benchmark_lightrag_omniroute.ps1
```

Проверить OmniRoute container, API, chat route и LightRAG smoke:

```bash
.\scripts\check_omniroute.ps1
```

Smoke-query persistent curated LightRAG memory:

```bash
.\scripts\query_lightrag_curated.ps1
```

Экспортировать persistent LightRAG graph в локальный HTML viewer:

```bash
.\scripts\export_lightrag_graph.ps1
```

Проверить экспорт LightRAG graph без открытия browser:

```bash
.\scripts\check_lightrag_graph_export.ps1
```

Запустить локальный server для viewer-а LightRAG graph:

```bash
.\scripts\serve_lightrag_graph.ps1
```

Остановить локальный server viewer-а LightRAG graph:

```bash
.\scripts\serve_lightrag_graph.ps1 -Stop
```

Локальный pre-commit checklist без LLM-зависимостей:

```bash
.\scripts\pre_commit_check.ps1
```

Проверить, что secrets не попали в tracked files, а локальные runtime `.env` остаются ignored:

```bash
.\scripts\check_secret_leaks.ps1
```

Более тяжелая проверка Git history:

```bash
.\scripts\check_secret_leaks.ps1 -IncludeGitHistory
```

Показать regenerable runtime/cache artifacts для безопасной чистки:

```bash
.\scripts\clean_runtime_artifacts.ps1
```

Удалить найденные runtime/cache artifacts:

```bash
.\scripts\clean_runtime_artifacts.ps1 -Apply
```

Проверить, что user-facing labels и messages остаются русифицированными:

```bash
.\scripts\check_user_facing_russian.ps1
```

Найти большие markdown-файлы и секции-кандидаты для curated memory shards:

```bash
.\scripts\suggest_knowledge_shards.ps1
```

## Запуск системы

Запустить dashboard:

```bash
uv run streamlit run src/stat_arb/dashboard/app.py
```

CLI examples:

```bash
# Ingest data
uv run stat-arb data ingest --symbols BTC/USDT,ETH/USDT --exchange binance --timeframe 15m

# Generate hypotheses
uv run stat-arb hypothesis generate --method sector --limit 10

# Run full experiment
uv run stat-arb experiment run --hypothesis-id <uuid>

# View experiment status
uv run stat-arb experiment list --status completed
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
│   ├── storage/            # Database и LightRAG interfaces
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
│   ├── lightrag/           # LightRAG storage
│   ├── vector_store/       # Embedded vector store
│   └── reports/            # Generated reports
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

Ingest cryptocurrency data:

```bash
uv run stat-arb data ingest \
  --symbols BTC/USDT,ETH/USDT \
  --exchange binance \
  --timeframe 15m \
  --start-date 2024-07-01 \
  --end-date 2025-01-01
```

Screen pairs by sector:

```bash
uv run stat-arb hypothesis generate \
  --method sector \
  --sector technology \
  --limit 20
```

Statistical tests:

```bash
uv run stat-arb test statistical \
  --asset-a BTC/USDT \
  --asset-b ETH/USDT \
  --train-window 60 \
  --test-window 30
```

Backtest и report:

```bash
uv run stat-arb backtest run \
  --hypothesis-id <uuid> \
  --entry-threshold 2.0 \
  --exit-threshold 0.5 \
  --generate-report
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

- Все agent decisions логируются в LightRAG.
- Все experiments отслеживаются в SQLite registry.
- Audit trails нужны для compliance.

## Roadmap

### v1: Research Platform

- Data ingestion с quality validation.
- Hypothesis generation и novelty checking.
- Statistical testing: cointegration, ADF, hedge ratio.
- Walk-forward backtesting с cost attribution.
- Critic review на bias и overfitting.
- LightRAG memory и knowledge graph.
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

- **LightRAG**: long-term memory и knowledge graph framework.
- **CCXT**: unified cryptocurrency exchange API.
- **Statsmodels**: statistical testing и econometrics.
- **Streamlit**: interactive dashboard framework.

## Контакты

- **GitHub**: [Cryptotehnolog](https://github.com/Cryptotehnolog)
- **Repository**: [STATISTICAL-ARBITRAGE](https://github.com/Cryptotehnolog/STATISTICAL-ARBITRAGE)
- **Issues**: [bugs и feature requests](https://github.com/Cryptotehnolog/STATISTICAL-ARBITRAGE/issues)
