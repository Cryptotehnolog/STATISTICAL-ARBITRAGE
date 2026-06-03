# Knowledge Decisions: Data Pipeline

This shard contains durable decisions about domain contracts, ingestion, data quality,
registry persistence, and deterministic OHLCV transformations.

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

Risks: Failed validation summaries are not yet written to ApeRAG by this helper. That
belongs behind the future Memory Agent boundary so registry writes do not depend on an LLM
gateway.

Update: Failed `DataQualityReport` objects can now be converted to policy-safe
`MemoryWriteRequest` records through `stat_arb.memory.data_quality_failure_memory_request`
and written through `write_data_quality_failure_memory`. Registry persistence remains
independent from the LLM gateway; runtime writes go through `MemoryAgentService`.

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

## DEC-0020: Make resampled OHLCV dataset IDs deterministic

Status: accepted

Decision: Resampled `OHLCVBatch` outputs use deterministic UUIDv5 dataset IDs derived from
the source dataset ID, symbol, source timeframe, target timeframe, output timestamp range,
and output bar count.

Rationale: Property-based resampling idempotence tests found that repeated resampling of
the same input produced equivalent bars but different generated dataset IDs. Dataset IDs are
part of downstream registry provenance, so repeated deterministic transformations should
produce stable identifiers.

Alternatives considered: Ignore dataset IDs in property tests; keep random IDs for every
transformation; add an optional caller-supplied output ID.

Risks: If the resampling identity fields change later, downstream registry references may
need a migration or explicit versioned identity scheme.

## DEC-0021: Align pair OHLCV batches by shared timestamps

Status: accepted

Decision: Use `stat_arb.data_quality.align_ohlcv_pair` as the deterministic boundary for
pair timestamp alignment. The function accepts two `OHLCVBatch` contracts, keeps only
shared timestamps, returns aligned batches plus dropped-bar counts, and can require full
overlap or a minimum overlap ratio.

Rationale: Statistical testing should not infer alignment from two independent series.
Keeping alignment in the data-quality layer gives later cointegration and backtesting code
two batches with identical timestamp order and explicit provenance metadata.

Alternatives considered: Align inside the Statistical Testing Agent; use pandas joins as
the runtime contract; silently forward unmatched bars downstream.

Risks: Partial overlap is allowed by default, so higher-level services should set
`min_overlap_ratio` or `require_full_overlap` when a strategy needs stricter data quality.

## DEC-0022: Guard statistical pair boundaries with explicit alignment

Status: accepted

Decision: Run `scripts/check_pair_alignment_boundary.ps1` in local pre-commit and CI. The
guard watches future pair/statistical modules and fails if they introduce pair testing
boundaries without an explicit `align_ohlcv_pair`, `PairAlignmentResult`, or
`aligned_timestamps` reference.

Rationale: Timestamp alignment is now a data-quality contract, not an optional detail left
to statistical tests. Adding the guard before the first statistical service prevents a
future module from accepting two raw `OHLCVBatch` series and silently comparing mismatched
timestamps.

Alternatives considered: Wait until the Statistical Testing Agent exists; rely on code
review only; put alignment checks inside every statistical function.

Risks: The guard is intentionally conservative and may need a narrow allowlist once the
statistical package layout becomes concrete.

## DEC-0023: Complete Data Agent property-test baseline

Status: accepted

Decision: Treat task 4 as complete only after property tests cover CCXT timestamp
normalization, missing-bar completeness, duplicate timestamp completeness, volume spike
sensitivity, resampling idempotence, and pair timestamp alignment.

Rationale: Data Agent correctness depends on invariants, not only example cases. The
property suite protects the data pipeline against silent timestamp shifts, undercounted
gaps, missed duplicate raw bars, missed outliers, unstable resampling, and mismatched pair
timestamps before Statistical Testing Agent work begins.

Alternatives considered: Leave optional property tests open; rely on example-based tests;
defer all property tests until production hardening.

Risks: Current `DataQualityReport` domain validation requires `end_date` to be after
`start_date`, so one-bar quality reports remain a separate contract decision.

## DEC-0025: Require JSON round-trip coverage for every domain entity

Status: accepted

Decision: Task 3.2 is complete only when every Pydantic domain entity has validation tests
and at least one JSON serialization/deserialization round-trip check. The round-trip
baseline covers hypotheses, datasets, OHLCV bars and batches, data quality issues and
reports, data-quality failure summaries, statistical tests, backtests, critic reviews,
experiments, and report artifacts.

Rationale: Agents will pass domain objects through files, registry boundaries, API
payloads, and memory summaries. A model that validates on construction but fails
serialization is not a stable contract.

Alternatives considered: Keep round-trip tests only for the first few models; rely on
Pydantic defaults; defer complete serialization tests until API endpoints exist.

Risks: Future domain entities must be added to the round-trip baseline when introduced.
