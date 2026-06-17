# Человеческий roadmap отложенной работы

Этот файл отвечает на простой вопрос: **что мы уже решили сделать позже, почему не
делаем это прямо сейчас и когда к этому возвращаться**.

Технические детали и точные ссылки хранятся в `docs/technical_debt.md` и
`docs/knowledge/future_ideas.md`. Здесь намеренно написано человеческим языком. Коды
`TD-0000` и `IDEA-0000` оставлены только как номера задач для контроля.

## Делать после нового runner, workflow или service boundary

- [ ] **Подключить audit trail действий агентов к реальным workflow** (`TD-0039`).
  Базовый безопасный контракт `AgentAuditEvent` и JSONL writer уже добавлены. Следующий
  шаг позже: чтобы каждый важный вызов агента оставлял понятный след: кто действовал, что
  сделал, зачем, с каким статусом, на какие registry/memory записи ссылается. В audit log
  нельзя писать secrets, raw logs или сырые payload.

- [ ] **Сравнить Engle-Granger с Kalman/Johansen/Phillips-Perron как отдельный research
  benchmark** (`TD-0040`).
  Это не замена текущего pipeline. Нужно сделать честное сравнение моделей на одинаковых
  данных: качество residuals, stability, turnover, out-of-sample результат и стоимость
  ошибок. Только после такого сравнения можно решать, какие методы включать в runtime.

- [ ] **Добавить event bus и heartbeat только когда появятся долгоживущие worker-агенты**
  (`TD-0041`).
  Сейчас агенты работают через явные service/CLI/registry boundaries. Event bus нужен не
  потому что “агентов много”, а когда будут persistent workers, live/paper services,
  асинхронные задачи и реальный риск stale/failed worker.

- [ ] **Расширить dashboard исследовательскими графиками из factual artifacts** (`TD-0042`).
  Позже dashboard должен показывать rolling metrics, распределения spread и correlation
  heatmap. Но графики должны строиться только из сохраненных registry/sidecar данных, а не
  из aggregate-only metrics.

- [ ] **Унифицировать retry policy для внешних API adapters** (`TD-0043`).
  CCXT adapter уже умеет bounded exponential retry. Позже стоит привести retry-отчеты
  разных adapters к общему failure-handling vocabulary, но не через грубый запрет “любой
  HTTP без retry”, а через точечные adapter tests.

- [ ] **Подготовить перенос на Ubuntu/server** (`TD-0001`, `TD-0015`).
  Нужны Linux-friendly команды, `.sh` wrappers или точные инструкции для `uv`, Docker,
  ApeRAG, Infisical, memory checks, SQLite, Parquet и CCXT smoke. Делать ближе к реальному
  server deployment.

- [x] **Добавить live CCXT smoke test** (`TD-0002`).
  Закрыто opt-in командой `.\scripts\check_live_market_data_acceptance.ps1`: Bybit-first
  smoke проверяет 50 active `USDT` swap symbols и пишет отчет в
  `data/live_market_data_acceptance/report.json`. Команда остается ручной readiness
  проверкой и не входит в pre-commit/CI, потому что сеть, rate limits и биржи нестабильны.

- [ ] **Добавить conversion helpers domain <-> storage** (`TD-0003`).
  Нужны только когда ingestion/validation/registry/CLI реально начнут переносить
  `OHLCVBatch`, `Dataset` или `DataQualityReport` через Parquet/SQLite boundary.

- [ ] **Автоматизировать seed памяти после крупных изменений** (`TD-0006`, `TD-0007`,
  `IDEA-0002`).
  Сейчас seed делает Codex вручную, потому что это stateful операция с внешними LLM. Позже
  можно сделать post-commit или scheduled workflow, если seed станет быстрым и стабильным.

- [ ] **Описать backup/restore для Infisical** (`TD-0008`).
  Перед удалением Docker volumes или rotation keys нужно понимать, что именно сохранять и
  как проверить восстановление.

- [ ] **Переизмерять порядок моделей OmniRoute** (`TD-0013`, `IDEA-0003`).
  Когда меняется аккаунт, provider или скорость моделей, нужно заново benchmark graph
  extraction и менять порядок не “на глаз”, а по фактам.

- [ ] **Сделать полноценный data ingestion CLI/service** (`TD-0014`).
  Команда должна fetch -> validate -> persist parquet -> write registry provenance. Нельзя
  добавлять простой downloader, который обходит quality report и registry.

- [ ] **Добавить answer-quality eval для agent RAG** (`TD-0019`).
  Сейчас есть deterministic answer-eval для ключевых вопросов проектной памяти: он
  проверяет обязательные факты и запрещенные ложные утверждения в retrieved ApeRAG context.
  Когда появится агент, который сам формирует финальный ответ по ApeRAG, нужно добавить
  отдельную проверку качества уже сгенерированного ответа: обязательные факты, запрет
  hallucinations, ссылки на decisions.

- [ ] **Добавить Cost Assumption Agent / service** (`TD-0020`).
  Он будет собирать и проверять fees, funding, borrow и slippage snapshots. Backtest Agent
  не должен брать старые плановые проценты как “рыночную правду”.

- [ ] **Довести factual report sidecars до полного runner** (`TD-0023`).
  Backtest уже умеет сохранять `backtest_series`, а Report Agent не строит графики из одних
  aggregate metrics. Следующий шаг: future full runner обязан всегда передавать factual
  series sidecars перед reporting.

- [ ] **Кэшировать novelty checks только если появится bottleneck** (`TD-0027`).
  Hypothesis Agent может спрашивать ApeRAG о похожих идеях. Кэш нужен только если real
  workflow покажет повторяющуюся latency.

- [ ] **Оптимизировать производительность только после profiler output** (`TD-0028`).
  Parallel pair scanning, regime vectorization, walk-forward caching, columnar storage и Rust
  должны идти после измерений, а не из желания “сделать быстрее заранее”.

- [ ] **Добавить regime-break exits только как explicit policy** (`TD-0029`).
  Сейчас regime detection является diagnostic evidence. Автоматический выход из позиции
  меняет стратегию и должен быть отдельной воспроизводимой policy.

- [ ] **Добавить ingestion watermarks и gap repair** (`TD-0030`).
  Data Agent должен понимать свежесть датасета и уметь добирать только пропущенные окна.

- [ ] **Сделать atomic Coordinator task claiming перед multi-worker режимом** (`TD-0031`).
  Сейчас очередь достаточна для local deterministic workflow. Перед несколькими worker
  processes нужен atomic claim, race-condition test и индекс по queue fields.

- [ ] **Добавить dashboard approval controls** (`TD-0035`).
  UI-кнопки approve/reject/quarantine можно делать только через audited Coordinator action,
  с actor, reason, status и memory-write result. Прямых mutation из dashboard быть не должно.

- [ ] **Сделать полный experiment runner** (`TD-0038`).
  Сейчас есть безопасный narrow pipeline `backtesting -> reporting`. Большая кнопка “run full
  experiment” появится только когда каждый stage будет иметь explicit payload, registry
  artifacts и factual outputs для следующего stage.

- [ ] **Сделать визуализацию работы агентов** (`IDEA-0006`).
  Идея вдохновлена `patoles/agent-flow`: live graph, timeline, transcript, tool calls и file
  attention. Делать позже, когда наши агенты начнут писать structured events. Бренд, logo и
  exact UI не копировать.

## Делать только после отдельного архитектурного решения

- [ ] **Проверить Chroma только при реальной необходимости** (`TD-0005`, `IDEA-0001`).
  ApeRAG сейчас active backend. Chroma не трогаем, пока нет конкретной причины.

- [ ] **Переходить к Rust только после profiling hotspot** (`TD-0010`).
  Rust остается путем ускорения, но не ранним rewrite. Перед Rust нужен Python reference,
  stable API, tests, benchmark и Windows/Ubuntu build check.

- [ ] **Добавить три будущие роли для paper/live trading** (`TD-0032`).
  Мы действительно планируем три будущие роли, но они не делают систему production-ready сами
  по себе:
  - `Regime Switch Detector`: проверяет смену рыночного режима сначала как research signal.
  - `Execution and Slippage Simulator`: моделирует комиссии, spread, slippage, funding и
    liquidity сначала как deterministic Backtest/Critic service.
  - `Dynamic Risk and Capital Allocator`: задает risk policy для exposure, drawdown,
    correlated positions и capital allocation сначала как explicit contracts.

  Почему не сейчас: проект пока research-first. Для paper/live нужны approvals, monitoring,
  kill switch, incident handling, execution gateway, audit logs и risk policies.

- [ ] **Использовать Jesse MCP только как reference checklist** (`TD-0033`, `IDEA-0007`).
  Полезны идеи по pairs trading, risk tools, jobs и certification gates. Нельзя подключать
  как runtime dependency или давать live trading tools без отдельного решения.

- [ ] **Развивать multi-asset statistical arbitrage поэтапно** (`TD-0037`).
  Будут cross-asset spreads, factor exposure, session-aware data, portfolio risk allocation
  и asset-class-specific adjustments, но только после стабильного pair pipeline и risk/data
  boundaries.

- [ ] **Оценивать внешние RAG/LLM eval репозитории как источники идей, не зависимости**
  (`IDEA-0008`).
  `hparreao/Awesome-AI-Evaluation-Guide` полезен как карта evaluation practices.
  `AIAnytime/rag-evaluator` полезен как пример reference-based metrics, но его BLEU/ROUGE-
  style подход не стоит ставить в проект без отдельного spike.

- [ ] **Проверить Recursive Language Models как sandbox-spike, не как замену ApeRAG**
  (`IDEA-0009`).
  RLMs могут быть полезны для длинных документов и глубокого reasoning по большому
  контексту, но это execution harness с sandbox-рисками. Сначала только read-only
  сравнение на наших curated questions, required facts, latency, cost и hallucination
  checks.

- [ ] **Проверить Context Engine как будущий routing layer** (`IDEA-0010`).
  Идея из статьи Vikram Moorjani: не выбирать один backend “на все случаи”, а маршрутизировать
  задачу по ограничениям: скорость, точность, цена, допустимость ошибки и требование к
  источникам. Для нас это значит: ApeRAG остается durable memory, RLM может стать отдельным
  sandboxed reasoning mode, а router появится только когда будет минимум два проверенных
  режима. Важно: routing не должен скрывать provenance от registry/audit и не должен
  обходить Memory Agent policy.

## Уже закрыто, но надо наблюдать

- [x] **MVP CLI/scripted workflows закрыты** (`Task 15`).
  Полный arbitrary runner вынесен в `TD-0038`.

- [x] **CI/testing baseline закрыт** (`Task 18`).
  CI не должен зависеть от local services, secrets, ApeRAG, Infisical или OmniRoute.

- [x] **GitHub Actions обновлен под Node.js 24-compatible actions** (`TD-0016`).
  Workflow использует `actions/checkout@v6`, `actions/setup-python@v6` и
  `astral-sh/setup-uv@v8.2.0`; CI после обновления зеленый.

- [x] **One-bar DataQualityReport решен как diagnostic report** (`TD-0018`).
  Если пришла только одна свеча, система теперь сохраняет не “чистый отчет качества”, а
  диагностический след: `is_valid=false`, `passed=false`,
  `invalid_reason="insufficient_data"` и issue `insufficient_data`. Это нужно, чтобы агенты
  не приняли одну свечу за полноценные проверенные данные. `Dataset` по-прежнему требует
  `end_date > start_date`.

- [x] **Базовый deterministic answer-eval для проектной памяти добавлен** (`TD-0019` baseline).
  `scripts/check_memory_quality.ps1` теперь проверяет не только “память отвечает на поиск”,
  но и “память не говорит опасную ерунду” по ключевым вопросам: one-bar
  `DataQualityReport`, ApeRAG/RLM/Context Engine boundaries. Это не заменяет будущую
  проверку финальных ответов агентов, но уже ловит отсутствие обязательных фактов и
  запрещенные ложные утверждения в retrieved ApeRAG context.

- [x] **Report Agent не строит полные графики из aggregate-only metrics** (`TD-0023` core).
  Остаток относится к future full runner.

- [x] **Ручная очистка временных файлов описана как безопасная ручная операция**
  (`TD-0011`).
  `docs/runtime_maintenance.md` объясняет, когда запускать
  `scripts/clean_runtime_artifacts.ps1`, почему сначала нужен dry-run, что удаляется, и
  какие persistent данные нельзя трогать обычной cleanup-командой.

- [x] **Тестируемость CLI/dashboard усилена без жестких UI coverage gates**
  (`TD-0036`).
  CI уже измеряет `stat_arb.cli` и `stat_arb.dashboard`; dashboard получил отдельный
  `presentation` helper module для labels, metric formatting и visible-column projection.
  Это дает focused tests без brittle Streamlit UI checks. Строгие отдельные UI gates пока
  не нужны: они начнут мешать больше, чем помогать.
