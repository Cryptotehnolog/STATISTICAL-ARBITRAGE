# Аудит перед переходом к Backtest Agent

Дата: 2026-06-04

## Вывод

Проект готов к переходу от пунктов 1-6 к пункту 7 `Build Backtest Agent`.

Предыдущая быстрая проверка была checkpoint-проверкой, а не полным аудитом. Этот отчет фиксирует более глубокую проверку: состояние `.kiro/tasks.md`, локальный pre-commit, CI, ApeRAG memory health, graph export, data pipeline checkpoint и поиск явных технических хвостов.

## Проверено

- `.kiro/specs/quant-research-architecture/tasks.md`: пункты 1, 2, 3, 4, 5 и 6 закрыты.
- `scripts/pre_commit_check.ps1`: прошел полностью, включая Ruff, unit tests, secret leak guard, русификацию user-facing текста, memory contract guard, pair alignment boundary guard и legacy memory backend guards.
- Unit baseline: 154 tests passed.
- GitHub Actions CI: run `26921029631` passed.
- ApeRAG memory health: project memory, graph, API, embedding endpoint и separate agent memory collection прошли.
- ApeRAG graph export: `251 nodes / 237 edges`, `docs/knowledge_graph/graph.json` валиден.
- Data pipeline checkpoint: ingestion, validation, Parquet, registry sidecars и memory boundary прошли вместе.
- Legacy LightRAG search: рабочий backend-код удален; оставшиеся строки находятся только в guard-patterns/tests, которые запрещают вернуть legacy backend.
- Поиск `TODO/FIXME/HACK/NotImplemented`: рабочих заглушек не найдено. Найденный `pass` в `ApeRAGMemoryClient.ensure_collection` является ожидаемым control flow при отсутствии collection.

## Исправлено во время аудита

- `scripts/check_aperag_knowledge.ps1` больше не использует фиксированные keywords `ApeRAG/memory/backend`.
- Добавлены query-aware keywords через `-Query` и явный override через `-Keywords`.
- Добавлен строгий semantic marker через `-ExpectedText`, чтобы readiness smoke мог проверять, что retrieved context действительно содержит ожидаемый decision/contract marker.
- Добавлены unit tests, запрещающие возврат старых hardcoded keywords.

## Остаточные риски

- ApeRAG knowledge check теперь проверяет retrieval quality, но не является полноценной LLM answer evaluation. Когда агенты начнут отвечать через ApeRAG, нужен отдельный answer-quality eval.
- GitHub Actions сообщает предупреждение о будущей миграции Node.js 20 actions. Это не ломает CI сейчас, но должно быть закрыто до принудительного перехода GitHub.
- Statistical Testing Agent принимает уже aligned arrays. Это правильно для boundary, но первый Backtest/Coordinator caller должен явно использовать alignment result перед statistical/backtest boundary.
- Regime detection сейчас реализован как rolling-statistics screen. Это допустимо для MVP, но не равно полноценному Chow-test implementation.

## Следующий безопасный шаг

Начинать пункт 7.1: core Backtest Agent. Первый маленький boundary должен опираться на уже готовые Z-score signals, hedge ratio, aligned timestamps, registry provenance и DataQualityReport checks.
