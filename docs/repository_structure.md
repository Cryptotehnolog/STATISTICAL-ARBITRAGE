# Структура репозитория

Проект использует local-first layout Python-пакета для research platform Statistical
Arbitrage. Пользовательская документация хранится в `docs/` и `README.md`; internal memory
для агентов хранится отдельно в `docs/knowledge/`.

## Верхний уровень

- `.kiro/specs/` содержит planning specifications и breakdown задач. Это исходные
  проектные артефакты.
- `data/` содержит runtime data, локальные databases, LightRAG stores, vector indexes и
  временные test artifacts. Директория намеренно ignored.
- `docs/` содержит пользовательскую и проектную документацию, которую нужно коммитить.
- `docs/technical_debt.md` содержит tracked backlog для всех “сделаем потом” follow-up,
  которые не должны оставаться только в чате.
- `docs/knowledge/` содержит internal curated memory shards для агентов и LightRAG. Эти
  файлы могут оставаться на английском, потому что это машинно-ориентированный слой.
- `docs/knowledge_graph/` содержит generated HTML viewer и JSON export для LightRAG. Эта
  директория ignored.
- `scripts/` содержит developer/operator scripts, в основном PowerShell wrappers для
  локальных проверок и рабочих процессов.
- `infra/infisical/` содержит локальный Docker Compose stack для self-host Infisical.
  Реальный `infra/infisical/.env` ignored и не должен попадать в Git.
- `src/stat_arb/` содержит importable Python package code.
- `tests/` содержит automated tests, разделенные по типам.

## Python package layout

- `src/stat_arb/agents/` будет содержать implementations агентов.
- `src/stat_arb/backtest/` будет содержать backtesting engines и cost attribution logic.
- `src/stat_arb/cli/` будет содержать CLI command wiring.
- `src/stat_arb/dashboard/` будет содержать dashboard code.
- `src/stat_arb/domain/` содержит Pydantic domain models и validation contracts для
  research entities. Это runtime/API слой, не persistence layer.
- `src/stat_arb/memory/` содержит LightRAG configuration и client code.
- `src/stat_arb/models/` зарезервирован для future shared package models, если они
  понадобятся.
- `src/stat_arb/scripts/` содержит Python module entrypoints, которые можно запускать через
  `python -m`.
- `src/stat_arb/secrets/` содержит Infisical REST client и configuration для загрузки
  runtime secrets через Universal Auth.
- `src/stat_arb/statistical/` будет содержать statistical testing logic.
- `src/stat_arb/storage/` содержит Structured Registry database layer. `storage/models.py`
  — SQLAlchemy ORM, а не domain/Pydantic models.
- `src/stat_arb/utils/` содержит shared utilities.

## Границы моделей

- SQLAlchemy persistence models живут в `src/stat_arb/storage/models.py`.
- Pydantic/domain models живут в `src/stat_arb/domain/`.
- Runtime data не должна жить внутри `src/`; package code должен оставаться importable и
  reproducible без локальных caches.

## Тесты

- `tests/unit/` содержит быстрые isolated unit tests.
- `tests/integration/` содержит integration tests, которые могут обращаться к локальным
  services или более тяжелым dependencies.
- `tests/property/` содержит property-based tests.
- Tests с marker `slow` исключены из default unit baseline.

## Локальные проверки

- `scripts/check_unit.ps1` запускает быстрый unit baseline.
- `scripts/check.ps1` запускает Ruff и быстрый unit baseline; эту команду нужно выполнять
  перед commit.
- `scripts/pre_commit_check.ps1` запускает local pre-commit checklist без LLM dependencies.
- `scripts/check_secret_leaks.ps1` проверяет, что runtime `.env` ignored, sensitive files
  не tracked, а tracked content не содержит типовые secret patterns.
- `scripts/clean_runtime_artifacts.ps1` показывает и удаляет regenerable runtime/cache
  artifacts без затрагивания persistent LightRAG storage, Infisical `.env` или Docker
  volumes.
- `scripts/seed_lightrag.ps1` загружает измененные curated project sources в local LightRAG
  storage.
- `scripts/seed_lightrag_omniroute.ps1` делает preview/apply ограниченного OmniRoute-backed
  knowledge seed.
- `scripts/seed_lightrag_curated.ps1` делает preview/apply только для
  `docs/knowledge/*.md` shards.
- `scripts/suggest_knowledge_shards.ps1` показывает большие markdown files и candidate
  sections для curated memory shards.
- `scripts/check_omniroute.ps1` проверяет OmniRoute container health, API models, chat и
  LightRAG smoke.
- `scripts/init_infisical_env.ps1` создает локальный ignored `.env` для self-host
  Infisical без вывода secrets в консоль.
- `scripts/start_infisical.ps1` запускает локальный Infisical Docker stack.
- `scripts/check_infisical.ps1` проверяет Docker services и `/api/status` локального
  Infisical.
- `scripts/check_infisical_auth.ps1` проверяет Infisical Universal Auth и чтение test
  secret без вывода secret value в консоль.
- `scripts/smoke_lightrag_omniroute.ps1` запускает маленький isolated LightRAG + OmniRoute
  graph extraction smoke test.
- `scripts/query_lightrag_curated.ps1` проверяет, что persistent curated LightRAG memory
  отвечает на проектные вопросы.
- `scripts/export_lightrag_graph.ps1` экспортирует persistent LightRAG GraphML в
  `docs/knowledge_graph/`.
- `scripts/check_lightrag_graph_export.ps1` проверяет, что экспорт LightRAG GraphML создает
  валидные непустые viewer files.
- `scripts/serve_lightrag_graph.ps1` экспортирует и запускает/останавливает локальный
  server viewer-а LightRAG graph на `127.0.0.1`.
- `scripts/open_lightrag_graph.ps1` поднимает server viewer-а LightRAG graph при
  необходимости и открывает локальный URL в browser.
- `scripts/create_lightrag_graph_shortcut.ps1` создает локальный desktop shortcut для
  запуска `open_lightrag_graph.ps1`.
- `scripts/benchmark_lightrag_omniroute.ps1` сравнивает OmniRoute models на одном LightRAG
  extraction document.
