# Knowledge Decisions: Data Transformations

This shard contains durable decisions about deterministic OHLCV transformations,
pair alignment, property-test coverage, and data-pipeline checkpoints.

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

Update: Partial overlap is no longer a hidden default. Callers must pass
`require_full_overlap` and `min_overlap_ratio` explicitly, because overlap policy is a
research-impacting assumption before statistical testing.

Risks: Call sites are more verbose. This is intentional: higher-level services and agents
must choose and persist the overlap policy they used.

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

Update: One-bar `DataQualityReport` is now a valid diagnostic report. The report contract
allows `start_date == end_date`, while the stricter `Dataset` contract still requires
`end_date` after `start_date` for research-ready data.

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

## DEC-0026: Use a deterministic checkpoint for Data Agent readiness

Status: accepted

Decision: Use `scripts/check_data_pipeline.ps1` as the task 5 readiness command. The
checkpoint uses fake CCXT rows and an in-memory SQLite registry to verify ingestion,
quality validation, Parquet persistence, registry rows, JSON sidecars, and failed quality
memory writes through `MemoryAgentService`.

Rationale: Checkpoint 5 should prove existing data-pipeline boundaries work together
without depending on live exchange availability, Docker, Infisical, OmniRoute, or ApeRAG
runtime latency.

Alternatives considered: Call a live CCXT exchange; rely only on unit tests; run a manual
sequence of separate commands.

Risks: Live exchange smoke remains a separate opt-in follow-up because rate limits and
network behavior should not block the fast local checkpoint.
