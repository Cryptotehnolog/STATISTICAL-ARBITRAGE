# Чеклист отложенной работы

Этот файл нужен для контроля всех “сделаем потом”. Подробные причины, риски и связи
хранятся в `docs/technical_debt.md`; здесь короткий human-facing контрольный список.

Правило: если новая идея или хвост не реализуется сразу, он должен попасть сюда,
в `docs/technical_debt.md` или в `.kiro/specs/quant-research-architecture/tasks.md`.
Нельзя оставлять важное только в чате.

## Можно закрывать до Task 19, если не расширяем архитектуру

- [ ] TD-0011: Описать ручную очистку runtime/cache артефактов и когда безопасно запускать
  `scripts/clean_runtime_artifacts.ps1`.
- [ ] TD-0016: Обновить GitHub Actions под Node.js 24-compatible actions после проверки
  актуальных upstream versions.
- [ ] TD-0018: Принять и реализовать решение по one-bar `DataQualityReport`: явный отказ
  до создания report или официально валидный diagnostic report.
- [ ] TD-0036: Продолжать вынос dashboard/CLI projection logic в тестируемые helpers; строгие
  package-specific coverage gates включать только после этого.

## Делать только после нового boundary или runner

- [ ] TD-0001 / TD-0015: Ubuntu portability hardening и подробный migration checklist.
- [ ] TD-0002: Live CCXT smoke test, только opt-in и вне fast pre-commit.
- [ ] TD-0003: Domain <-> parquet/storage conversion helpers, только когда появится
  реальная service boundary, которой они нужны.
- [ ] TD-0006 / TD-0007: Knowledge seeding automation и синхронизация curated shards после
  крупных изменений `.kiro`/docs.
- [ ] TD-0008: Infisical backup/restore discipline перед удалением Docker volumes или
  rotation keys.
- [ ] TD-0013: OmniRoute model-order rebenchmark при изменении provider behavior.
- [ ] TD-0014: Service-level data ingestion CLI, только через quality/provenance/registry.
- [ ] TD-0019: Agent RAG answer-quality eval после появления agent answer boundary.
- [ ] TD-0020: Cost Assumption Agent для verified/manual-approved cost snapshots.
- [ ] TD-0023: Full experiment runner должен передавать factual series sidecars в registry
  перед reporting.
- [ ] TD-0027: Hypothesis novelty cache только после измеримой latency в real workflow.
- [ ] TD-0028: Profile-guided performance work после workflow runner и profiler output.
- [ ] TD-0029: Regime-break exit только через explicit research policy.
- [ ] TD-0030: Registry-backed ingestion watermarks и gap repair.
- [ ] TD-0031: Atomic Coordinator task claiming перед multi-worker execution.
- [ ] TD-0035: Dashboard approval controls через audited Coordinator action после UX failure
  handling.
- [ ] TD-0038: Arbitrary full experiment runner после mature stage boundaries для всех
  этапов.
- [ ] IDEA-0006: Agent execution observability UI inspired by `patoles/agent-flow`: live
  graph, timeline, transcript, tool calls и file attention на наших structured agent
  events. Не копировать бренд, logo или exact UI; строить собственный project-native view.

## Не делать без отдельного архитектурного решения

- [ ] TD-0005 / IDEA-0001: Chroma compatibility spike, только если появится конкретная
  потребность вне ApeRAG.
- [ ] TD-0010: Rust implementation, только после profiling hotspot, Python reference tests,
  stable API boundary и Windows/Ubuntu build check.
- [ ] TD-0032: Future paper/live trading roles, только после research MVP, approvals,
  failure handling и risk policies. Роли зафиксированы как staged roadmap, а не обещание
  production-ready:
  - Regime Switch Detector: сначала research-time regime robustness validation.
  - Execution and Slippage Simulator: сначала deterministic Backtest/Critic service boundary.
  - Dynamic Risk and Capital Allocator: сначала explicit risk policy contracts.
- [ ] TD-0033 / IDEA-0007: Jesse MCP использовать только как reference checklist, не как
  runtime dependency.
- [ ] TD-0037: Multi-asset statistical arbitrage roadmap, только поэтапно после стабильного
  pair pipeline, quality/provenance и risk boundaries.
- [ ] IDEA-0002: Автоматический post-commit seed, только если seed runs станут быстрыми и
  стабильными.
- [ ] IDEA-0003: Graph extraction provider benchmark, когда provider behavior изменится или
  качество графа начнет деградировать.

## Закрыто или почти закрыто, но требует наблюдения

- [x] Task 15 MVP CLI/scripted workflows: закрыт как safe local execution baseline.
  Полный arbitrary runner вынесен в TD-0038.
- [x] Task 18 CI/testing baseline: закрыт; CI не должен зависеть от local services/secrets.
- [x] TD-0023 core guard: Report Agent не строит full charts из aggregate-only metrics.
  Остаток относится к будущему full runner.
