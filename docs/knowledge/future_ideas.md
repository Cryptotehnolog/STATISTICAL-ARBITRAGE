# Будущие идеи

Этот файл собирает идеи, найденные во время разработки. Их стоит рассмотреть позже, но они
не должны отвлекать от текущей задачи. Codex должен добавлять сюда долговечные идеи,
которые возникают при implementation или review, а LightRAG seed command затем будет их
загружать.

## IDEA-0001: Chroma compatibility spike

Status: proposed

Idea: Проверить, поддерживает ли более новая или иначе установленная сборка LightRAG
`ChromaVectorDBStorage`, какие dependencies нужны и можно ли запускать Chroma embedded без
Docker для local MVP.

Why later: FAISS сейчас работает и держит MVP маленьким. Chroma стоит принимать только если
он дает явную operational или retrieval benefit.

## IDEA-0002: Автоматизировать knowledge seed после успешных task commits

Status: proposed

Idea: Добавить optional local workflow, который запускает knowledge seed command после
commits, затрагивающих `README.md`, `.kiro/specs/`, `docs/` или architecture-relevant source
files.

Why later: Seed command пишет local runtime state и может загружать embeddings, поэтому он
должен оставаться opt-in, пока workflow не станет доказанно стабильным и достаточно
быстрым.

## IDEA-0003: Benchmark LightRAG graph extraction providers

Status: proposed

Idea: Добавить benchmark command, который прогоняет один tiny LightRAG graph extraction
document через каждую настроенную OpenAI-compatible model или combo и записывает latency,
extracted nodes, extracted edges и status.

Why later: OmniRoute smoke test валидирует текущий active combo, но порядок models внутри
`my-ai` должен основываться на extraction quality и latency, измеренных на реальном
LightRAG prompt, а не только на dashboard ping tests.

## IDEA-0004: Разбить большие Kiro design knowledge на curated memory shards

Status: implemented

Idea: Вынести долговечные architecture decisions, interface contracts и implementation
notes из больших Kiro design files в меньшие markdown shards внутри `docs/knowledge/`.

Outcome: Добавлены curated shards для MVP scope, agent memory contracts, research workflow
contracts и safety/testing acceptance. Добавлен suggestion script, который помогает находить
будущие большие markdown candidates.

## IDEA-0005: Controlled rebuild LightRAG storage для русифицированного graph

Status: proposed

Idea: Добавить безопасную команду rebuild, которая делает backup текущего `data/lightrag`,
создает чистое runtime storage и заново seed только `docs/knowledge/*.md` через
OpenAI-compatible provider с русским system prompt.

Why later: Перевод curated shards и повторный `-Force` обновляют retrieval/query, но старые
англоязычные entities, relationships и LLM cache могут оставаться в persistent graph.
Для русифицированной визуализации нужен controlled rebuild, а не ручная правка generated
`graph.json`.
