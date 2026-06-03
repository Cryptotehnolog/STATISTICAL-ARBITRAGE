# Knowledge Decisions

This file is a curated source for project decisions that should be seeded into LightRAG.
Keep entries concise, factual, and durable. Runtime logs, raw prompts, secrets, and bulky
metrics do not belong here.

## DEC-0001: Use FAISS for the local MVP LightRAG backend

Status: accepted

Decision: Use LightRAG with `FaissVectorDBStorage` as the default local vector backend.
Keep `NanoVectorDBStorage` as a lightweight supported alternative.

Rationale: The current installed LightRAG build imports FAISS storage successfully, while
Chroma storage is not available in this environment. FAISS keeps the MVP local-first and
avoids Docker or a separate vector service.

Alternatives considered: Chroma, NanoVectorDB.

Risks: Chroma may still be useful later, but it needs a separate compatibility spike before
being advertised as an active runtime backend.

## DEC-0002: Keep runtime data outside the Python package

Status: accepted

Decision: Runtime storage, SQLite databases, LightRAG data, vector indexes, reports, logs,
and scratch data must live under top-level ignored directories such as `data/`, not under
`src/stat_arb/`.

Rationale: Package code should stay importable, reviewable, and reproducible without local
runtime artifacts mixed into source directories.

Risks: Scripts must consistently resolve paths from the repository root.

## DEC-0003: Keep knowledge seeding explicit but automatic

Status: accepted

Decision: Knowledge seeding should be a dedicated command that automatically gathers curated
project sources and writes changed documents to LightRAG. It should not run as part of the
fast unit check.

Rationale: Seeding loads the embedding model and writes runtime state, so coupling it to
`scripts/check.ps1` would make every commit check slower and stateful.

Risks: Developers must run the seed command when they want local LightRAG memory updated.
This can later be automated through a post-commit or scheduled local workflow if needed.

## DEC-0004: Use no-op LLM fallback until an optional LLM provider is enabled

Status: accepted

Decision: Provide a local no-op `llm_model_func` by default so LightRAG can initialize and
store vector chunks without requiring API keys, network access, or a local LLM service.
Enable an OpenAI-compatible provider explicitly when graph extraction is needed.

Rationale: The current LightRAG build requires `llm_model_func` to be callable during
initialization even though the signature allows `None`. A no-op fallback keeps local
knowledge seeding available while the project has no configured LLM provider.

Alternatives considered: Block all LightRAG writes until an LLM provider exists; wire a
cloud LLM immediately.

Risks: Entity and relationship extraction remains empty with the no-op fallback, so this is
vector memory only until a real OpenAI-compatible LLM provider is enabled.

## DEC-0005: Use NanoVectorDB for automated knowledge seeding on Windows

Status: accepted

Decision: Default the knowledge seed command to `NanoVectorDBStorage`, while keeping FAISS
available through an explicit `--vector-store faiss` flag.

Rationale: FAISS storage works for initialization, but on this Windows workspace it logs
permission errors while replacing metadata files during repeated seed writes. NanoVectorDB
completes the same seed workflow without those file replacement errors.

Alternatives considered: Keep FAISS default for seed; require elevated seed runs.

Risks: Runtime experiment memory may still use FAISS by default. The backend choice should
be revisited once the memory agent and query workflows are implemented.

## DEC-0007: Use OmniRoute as the active LightRAG LLM gateway

Status: accepted

Decision: Use OmniRoute in Docker as the active OpenAI-compatible gateway for LightRAG
entity/relation extraction. Keep the project integration generic through the
`openai_compatible` provider and the `my-ai` combo instead of hard-coding one upstream
model.

Rationale: The earlier local CPU extractor was too slow for routine development.
OmniRoute through `my-ai` is faster on the same tiny LightRAG smoke document and provides
model fallback.

Alternatives considered: Keep a local CPU extractor as the primary path; use kiro-gateway
directly; wire each model as a separate container.

Risks: OmniRoute depends on external provider availability and account/session health.
Keep the no-op provider as the safe default and make provider smoke tests explicit.

Benchmark result: On the same tiny LightRAG extraction document, the measured model order
was `kiro/deepseek-3.2` (14 nodes / 15 edges), `kiro/glm-5` (13 nodes / 13 edges),
`kiro/claude-sonnet-4.5` (9 nodes / 13 edges), `kiro/minimax-m2.5` (10 nodes / 12 edges),
then `kiro/qwen3-coder-next` (14 nodes / 9 edges). Prefer this order for `my-ai` until a
new benchmark says otherwise.

## DEC-0008: Keep OmniRoute knowledge seeding opt-in and size-limited

Status: accepted

Decision: Use a dedicated OmniRoute seed wrapper that defaults to dry-run and applies
per-document and total character limits. Require an explicit apply flag before writing to
LightRAG through the LLM-backed provider.

Rationale: Curated project sources include large Kiro design documents. Sending those
documents through the LLM extraction path accidentally would make seed runs slow, expensive,
and hard to review.

Alternatives considered: Make the base seed command dry-run by default; seed every changed
document through OmniRoute automatically.

Risks: Large but useful sources may be skipped until they are split into smaller curated
documents.

## DEC-0009: Use curated knowledge shards instead of seeding large Kiro specs directly

Status: accepted

Decision: Keep `.kiro` specs as planning source documents and create smaller curated
markdown shards under `docs/knowledge/` for LightRAG seeding.

Rationale: Large design and requirements files contain useful context but are too bulky for
routine LLM-backed graph extraction. Curated shards produce cleaner entities and
relationships while preserving source references back to the original specs.

Alternatives considered: Split the `.kiro` specs themselves; seed the full design and
requirements files directly; rely only on README and decisions.

Risks: Curated shards can drift from source specs if not reviewed after major planning
changes. Use the shard suggestion script to find large sections that deserve extraction.

## DEC-0010: Self-host Infisical through an isolated Docker Compose stack

Status: accepted

Decision: Run Infisical locally through a dedicated Docker Compose stack containing the
Infisical backend, PostgreSQL, and Redis. Expose only the backend on localhost. Integrate
Python code through the Infisical REST API and Universal Auth instead of the Python SDK.

Rationale: Official self-host deployment expects backend, PostgreSQL, and Redis. The Python
SDK is not compatible with the project's Pydantic v2 baseline, while the REST API keeps the
integration small and testable.

Alternatives considered: Infisical Cloud only; a single standalone backend container; the
Python SDK.

Risks: The local `.env` encryption key and PostgreSQL volume are coupled. Losing the key
can make stored secrets unrecoverable, so local backup discipline is required before any
volume cleanup.

## DEC-0011: Separate Pydantic domain contracts from SQLAlchemy persistence models

Status: accepted

Decision: Keep Pydantic research entity models in `src/stat_arb/domain/` and SQLAlchemy
ORM models in `src/stat_arb/storage/models.py`.

Rationale: Agents and services need strict runtime validation contracts, while the
Structured Registry needs persistence mappings and relationships. Keeping these layers
separate avoids coupling API payload validation to database implementation details.

Alternatives considered: Reuse SQLAlchemy models as runtime contracts; put Pydantic models
under `src/stat_arb/models/`.

Risks: Field drift is possible between domain and storage layers. Conversion helpers should
be added when repository/service code starts moving data between them.

## DEC-0012: Require strict OHLCV and data quality domain contracts before CCXT ingestion

Status: accepted

Decision: Data Agent services must exchange normalized `OHLCVBar`, `OHLCVBatch`, and
`DataQualityReport` domain models instead of ad-hoc DataFrame or dictionary payloads.

Rationale: CCXT ingestion, data quality validation, statistical testing, and backtesting
all depend on the same candle semantics: UTC timestamps, valid OHLC bounds, ordered bars,
missing-bar counts, duplicate detection, outlier counts, and pass/fail quality decisions.
Making this contract executable before the adapter is implemented prevents downstream
agents from depending on informal payload shapes.

Alternatives considered: Start with raw DataFrames and add validation later; only document
the expected payload shape in markdown.

Risks: The domain contract may need narrow extensions once the first parquet/storage
service exists. Add conversion helpers only when a real service boundary needs them.

## DEC-0013: Keep CCXT ingestion separate from data quality validation

Status: accepted

Decision: Implement CCXT OHLCV ingestion as a narrow adapter under `stat_arb.ingestion`.
The adapter fetches exchange rows, normalizes them into `OHLCVBatch`, applies retry
behavior, and writes raw parquet partitions. Data quality reports, registry writes, and
LightRAG summaries remain separate tasks.

Rationale: Task 4.1 should prove source access and raw persistence without mixing in the
validation/reporting responsibilities from tasks 4.3, 4.9, and 4.10. Keeping ingestion
small makes it easier to test without network access and prevents Data Agent code from
returning informal payloads.

Alternatives considered: Put CCXT logic directly in a future Data Agent; combine ingestion,
quality validation, and registry writes in one service.

Risks: A thin adapter still needs a later live smoke test against a real exchange and a
service-level integration point once quality validation exists.

## DEC-0014: Validate OHLCV quality as deterministic domain logic

Status: accepted

Decision: Implement OHLCV quality validation under `stat_arb.data_quality` as deterministic
Python functions that return the existing `DataQualityReport` domain contract. The validator
detects missing bars, duplicate raw timestamps, abnormal volume spikes, and UTC-normalized
timestamps without calling live exchanges or LLM services.

Rationale: Data Agent workflows need a stable validation boundary before statistical tests
or backtests can trust ingested candles. Keeping validation separate from CCXT ingestion
preserves the narrow adapter from task 4.1 while giving future registry/reporting code a
strict pass/fail object.

Alternatives considered: Add validation directly inside the CCXT adapter; return ad-hoc
dictionaries; defer validation until the future Data Agent service.

Risks: `OHLCVBar` and `OHLCVBatch` already reject impossible candles and non-positive
prices, so runtime outlier reporting for those conditions requires a later raw-row
validation layer if ingestion should preserve malformed source rows for diagnostics.

## DEC-0015: Run fast Python CI on Ubuntu without external services

Status: accepted

Decision: Add a GitHub Actions workflow on `ubuntu-latest` for push, pull request, and
manual dispatch. The workflow installs dependencies with `uv`, runs user-facing Russian
text checks, secret leak checks, Ruff, and fast unit tests. It intentionally excludes
OmniRoute, Infisical auth, LightRAG seeding, and other local service checks.

Rationale: The project is developed on Windows but is expected to move to an Ubuntu server.
Running fast CI on Ubuntu catches portability issues early while keeping GitHub Actions
free from local secrets and long-running LLM dependencies.

Alternatives considered: Windows-only CI; running the local PowerShell `check.ps1`; adding
OmniRoute and Infisical integration checks to every push.

Risks: CI does not yet cover external service readiness, property tests, or reproducibility
checks. Those remain separate follow-up tasks under the CI section.

## DEC-0016: Add a narrow OHLCV ingestion pipeline boundary

Status: accepted

Decision: Use `stat_arb.ingestion.fetch_validate_write_ohlcv` as the first service
boundary that composes `CCXTOHLCVSource`, `validate_ohlcv_batch`, and raw Parquet
persistence.

Rationale: The Data Agent should not pass ad-hoc DataFrames or dicts between steps. A
narrow pipeline keeps the adapter focused on exchange access, keeps quality validation
deterministic, and writes Parquet only after the domain `DataQualityReport` passes.

Alternatives considered: Add validation into `CCXTOHLCVSource`; wait for a larger Data
Agent service; write Parquet first and quarantine failed batches afterward.

Risks: Failed quality validation raises `OHLCVQualityError` and does not write Parquet
files. Durable data-quality report storage, registry persistence, quarantine records, and
LightRAG summaries remain separate follow-up tasks.

## DEC-0017: Persist OHLCV quality reports in the registry with JSON sidecars

Status: accepted

Decision: Store validated OHLCV ingestion results through
`stat_arb.storage.persist_ohlcv_ingestion_result`. The helper writes a `datasets` row, a
`data_quality_reports` row, and deterministic JSON sidecars for dataset provenance and the
full quality report.

Rationale: The Structured Registry remains the source of truth for dataset IDs, quality
report IDs, pass/fail status, and numeric metrics. JSON sidecars keep the raw ingestion
artifact reproducible without making Parquet directories the only durable record.

Alternatives considered: Store only JSON next to Parquet; overload `ReportArtifact` before
an experiment exists; put registry writes directly inside the CCXT source adapter.

Risks: Failed validation summaries are not yet written to LightRAG by this helper. That
belongs behind the future Memory Agent boundary so registry writes do not depend on an LLM
gateway.

## DEC-0018: Keep data-quality failure summaries as pure contracts

Status: accepted

Decision: Use `DataQualityFailureSummary` and `summarize_data_quality_failure` as a pure
contract for future Memory Agent writes. The helper converts a failed `DataQualityReport`
into a concise summary with issue codes and a registry reference, without calling LightRAG
or writing storage state.

Rationale: Data Agent and registry code should not depend directly on an LLM gateway.
Structured metrics stay in the registry, while the future Memory Agent receives only a
small, memory-safe failure summary.

Alternatives considered: Write failed validation summaries directly to LightRAG from the
quality validator; store all issue details in LightRAG; wait until Memory Agent exists
before defining the contract.

Risks: The summary is intentionally concise. If later Memory Agent workflows need richer
context, add fields explicitly rather than passing the full raw report to LightRAG.

## DEC-0019: Resample OHLCV batches with deterministic domain rules

Status: accepted

Decision: Use `stat_arb.data_quality.resample_ohlcv_batch` to downsample `OHLCVBatch`
contracts into coarser timeframes. The target timeframe must be coarser than the source
timeframe and an exact multiple of it. Output timestamps are labeled by the UTC window
start. OHLCV aggregation uses first open, max high, min low, last close, and summed volume.

Rationale: Statistical tests and backtests need stable candle semantics before pair
alignment. Keeping resampling in the domain/data-quality layer avoids passing DataFrames
between agents and keeps deterministic behavior testable without live exchange access.

Alternatives considered: Use pandas resampling directly as the agent contract; silently keep
partial windows by default; allow arbitrary non-multiple target intervals.

Risks: Strict resampling drops incomplete windows by default. Callers can explicitly keep
partial windows for diagnostics, but production-quality datasets should validate gaps before
statistical testing.
