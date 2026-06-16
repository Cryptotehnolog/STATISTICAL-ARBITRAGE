# Knowledge Decisions: Data Pipeline

This shard contains durable decisions about domain contracts, ingestion, data quality,
and registry persistence. Deterministic OHLCV transformations live in
`docs/knowledge/decisions_data_transforms.md`.

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
Memory Agent summaries remain separate tasks.

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
Memory Agent summaries remain separate follow-up tasks.

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

Risks: Failed validation summaries must stay concise and must continue to flow through
the implemented Memory Agent policy boundary so registry writes do not depend directly on
an LLM gateway.

Update: Failed `DataQualityReport` objects can now be converted to policy-safe
`MemoryWriteRequest` records through `stat_arb.memory.data_quality_failure_memory_request`
and written through `write_data_quality_failure_memory`. Registry persistence remains
independent from the LLM gateway; runtime writes go through `MemoryAgentService`.

## DEC-0039: Use Bybit as the first crypto exchange for live CCXT smoke

Status: Accepted

Bybit is the first crypto venue for early live CCXT smoke and manual ingestion checks.
Binance, OKX, and Deribit remain active planned venues for cross-venue validation and
future derivatives research.

Excluded legacy venues are not part of the active project roadmap. They must not appear as
recommended exchanges in README examples, docs, or user-facing scripts.

Live CCXT smoke remains opt-in because exchange API checks depend on network state,
rate limits, regional availability, credentials, and terms of service. Pre-commit must
stay deterministic and must not depend on live exchange APIs.

## DEC-0066: Start Task 15 CLI with guarded data commands

Status: accepted

Decision: Implement the first CLI surface as `stat-arb data download`,
`stat-arb data validate`, and `stat-arb data list`. The download command composes the
existing CCXT source, deterministic OHLCV quality validation, Parquet persistence,
Structured Registry rows, and JSON sidecars. The validate command fetches and validates a
sample without writing registry state. The list command reads datasets from the registry.

Rationale: Task 15 should not begin with a full experiment runner. Data ingestion already
has quality/provenance rules, so the first CLI must expose those rules instead of adding a
shortcut around them. Research thresholds remain explicit command inputs.

Alternatives considered: Add a broad `experiment run` command first; provide a raw
`data ingest` command that writes Parquet without registry provenance; keep CLI work
blocked until report series sidecars exist. Those options would either bypass quality
boundaries or delay a useful operator entrypoint.

Verification: `scripts/check_cli_pipeline.ps1` runs CLI tests for dataset listing,
validation without registry writes, and download through the full guarded persistence
boundary.
