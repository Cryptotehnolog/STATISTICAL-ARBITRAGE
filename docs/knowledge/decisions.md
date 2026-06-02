# Решения для базы знаний

Этот файл является curated source для проектных решений, которые должны попадать в
LightRAG. Записи должны быть краткими, фактическими и долговечными. Runtime logs, raw
prompts, секреты и громоздкие метрики здесь не нужны.

## DEC-0001: Использовать FAISS как локальный MVP backend для LightRAG

Status: accepted

Decision: Использовать LightRAG с `FaissVectorDBStorage` как default local vector backend.
`NanoVectorDBStorage` оставить как легкую поддерживаемую альтернативу.

Rationale: Текущая установленная сборка LightRAG успешно импортирует FAISS storage, а
Chroma storage в этом окружении недоступен. FAISS сохраняет MVP local-first и не требует
Docker или отдельного vector service.

Alternatives considered: Chroma, NanoVectorDB.

Risks: Chroma может быть полезен позже, но перед объявлением его активным runtime backend
нужен отдельный compatibility spike.

## DEC-0002: Держать runtime data вне Python package

Status: accepted

Decision: Runtime storage, SQLite databases, LightRAG data, vector indexes, reports, logs и
scratch data должны жить в top-level ignored директориях, например `data/`, а не внутри
`src/stat_arb/`.

Rationale: Package code должен оставаться importable, reviewable и reproducible без
локальных runtime artifacts, смешанных с source directories.

Risks: Scripts должны consistently resolve paths от repository root.

## DEC-0003: Делать knowledge seeding явным, но автоматизированным

Status: accepted

Decision: Knowledge seeding должен быть отдельной командой, которая автоматически собирает
curated project sources и записывает измененные документы в LightRAG. Он не должен входить
в быстрый unit check.

Rationale: Seeding загружает embedding model и пишет runtime state. Если привязать его к
`scripts/check.ps1`, каждый commit check станет медленнее и stateful.

Risks: Разработчики должны запускать seed command, когда хотят обновить локальную LightRAG
memory. Позже это можно автоматизировать через post-commit или scheduled local workflow.

## DEC-0004: Использовать no-op LLM fallback до включения optional LLM provider

Status: accepted

Decision: По умолчанию предоставлять локальный no-op `llm_model_func`, чтобы LightRAG мог
инициализироваться и хранить vector chunks без API keys, network access или локального LLM
service. OpenAI-compatible provider включать явно, когда нужна graph extraction.

Rationale: Текущая сборка LightRAG требует, чтобы `llm_model_func` был callable при
инициализации, хотя signature допускает `None`. No-op fallback сохраняет local knowledge
seeding доступным, пока в проекте не настроен LLM provider.

Alternatives considered: Блокировать все LightRAG writes до появления LLM provider;
подключить cloud LLM сразу.

Risks: Entity и relationship extraction остаются пустыми с no-op fallback, поэтому это
только vector memory до включения реального OpenAI-compatible LLM provider.

## DEC-0005: Использовать NanoVectorDB для automated knowledge seeding на Windows

Status: accepted

Decision: Для knowledge seed command по умолчанию использовать `NanoVectorDBStorage`, а
FAISS оставить доступным через явный flag `--vector-store faiss`.

Rationale: FAISS storage работает для инициализации, но в этом Windows workspace логирует
permission errors при замене metadata files во время повторных seed writes. NanoVectorDB
проходит тот же seed workflow без этих file replacement errors.

Alternatives considered: Оставить FAISS default для seed; требовать elevated seed runs.

Risks: Runtime experiment memory все еще может использовать FAISS by default. Backend choice
нужно пересмотреть после реализации Memory Agent и query workflows.

## DEC-0007: Использовать OmniRoute как активный LightRAG LLM gateway

Status: accepted

Decision: Использовать OmniRoute в Docker как активный OpenAI-compatible gateway для
LightRAG entity/relation extraction. Интеграцию проекта держать generic через provider
`openai_compatible` и combo `my-ai`, а не hard-code конкретной upstream model.

Rationale: Предыдущий локальный CPU extractor был слишком медленным для регулярной
разработки. OmniRoute через `my-ai` быстрее на том же tiny LightRAG smoke document и дает
model fallback.

Alternatives considered: Оставить локальный CPU extractor primary path; использовать
kiro-gateway напрямую; подключать каждую model как отдельный container.

Risks: OmniRoute зависит от external provider availability и account/session health.
No-op provider остается safe default, а provider smoke tests должны запускаться явно.

Benchmark result: На одном tiny LightRAG extraction document измеренный порядок models:
`kiro/deepseek-3.2` (14 nodes / 15 edges), `kiro/glm-5` (13 nodes / 13 edges),
`kiro/claude-sonnet-4.5` (9 nodes / 13 edges), `kiro/minimax-m2.5` (10 nodes / 12 edges),
затем `kiro/qwen3-coder-next` (14 nodes / 9 edges). Этот порядок стоит использовать для
`my-ai`, пока новый benchmark не покажет другое.

## DEC-0008: Держать OmniRoute knowledge seeding opt-in и size-limited

Status: accepted

Decision: Использовать отдельный OmniRoute seed wrapper, который по умолчанию делает dry-run
и применяет per-document и total character limits. Для записи в LightRAG через LLM-backed
provider требуется явный apply flag.

Rationale: Curated project sources включают большие Kiro design documents. Случайная
отправка таких документов через LLM extraction path сделает seed runs медленными,
дорогими и сложными для review.

Alternatives considered: Сделать base seed command dry-run by default; автоматически seed
каждый changed document через OmniRoute.

Risks: Большие, но полезные sources могут быть пропущены, пока их не разобьют на smaller
curated documents.

## DEC-0009: Использовать curated knowledge shards вместо прямого seeding больших Kiro specs

Status: accepted

Decision: `.kiro` specs остаются planning source documents, а для LightRAG seeding создаются
меньшие curated markdown shards в `docs/knowledge/`.

Rationale: Большие design и requirements files содержат полезный контекст, но слишком
громоздки для регулярной LLM-backed graph extraction. Curated shards дают более чистые
entities и relationships, сохраняя source references на исходные specs.

Alternatives considered: Разделить сами `.kiro` specs; seed full design и requirements
files напрямую; полагаться только на README и decisions.

Risks: Curated shards могут drift от source specs, если их не review после крупных planning
changes. Shard suggestion script должен помогать находить большие sections, которые нужно
вынести.
