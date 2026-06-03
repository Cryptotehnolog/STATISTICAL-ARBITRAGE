# Knowledge Decisions: Statistical Testing

This shard contains durable decisions about statistical testing contracts, pair validation,
multiple-testing correction, and future Statistical Testing Agent boundaries.

## DEC-0027: Keep Engle-Granger cointegration as pure statistical logic

Status: accepted

Decision: Implement Engle-Granger cointegration testing under `stat_arb.statistical` as
pure Python functions that accept already aligned numeric price series and return a typed
`CointegrationTestResult`. The function validates shape, finite values, sample size, alpha,
and corrected p-value inputs before calling `statsmodels`.

Rationale: Pair timestamp alignment and data-quality checks belong upstream in the data
pipeline. Registry persistence and ApeRAG lesson writes belong later in the Statistical
Testing Agent integration step. Keeping the first cointegration boundary pure makes the
statistical behavior deterministic, fast to test, and safe to reuse in property tests.

Alternatives considered: Accept raw `OHLCVBatch` pairs directly; write test results to the
registry inside the cointegration helper; call ApeRAG directly from statistical functions.

Risks: The pure helper does not prove that callers used aligned data. Keep the existing
pair-alignment guard active until the full Statistical Testing Agent service enforces the
boundary explicitly.

## DEC-0028: Support explicit multiple-testing correction

Status: accepted

Decision: Provide `none`, `bonferroni`, and `benjamini_hochberg` p-value correction helpers.
The cointegration result keeps both the raw p-value and the corrected p-value, and pass/fail
decisions use the corrected value.

Rationale: Pair screening tests many candidate pairs, so raw p-values are not enough for a
reliable research workflow. Keeping correction explicit prevents the agent from silently
treating a single-test result and a multi-pair screening result as equivalent.

Alternatives considered: Always apply Bonferroni; always apply Benjamini-Hochberg; defer
correction until the future Hypothesis Agent.

Risks: The correction method must be selected at the service/workflow boundary once batch
pair screening exists.

## DEC-0029: Keep ADF residual stationarity testing pure

Status: accepted

Decision: Implement ADF stationarity testing under `stat_arb.statistical` as a pure helper
that accepts spread residuals, validates one-dimensional finite non-constant input, and
returns a typed `ADFTestResult`.

Rationale: Residual construction, hedge ratio estimation, registry persistence, and ApeRAG
lesson writes belong to later Statistical Testing Agent tasks. The ADF helper should only
answer whether the residual/spread series rejects the unit-root null under an explicit
alpha threshold.

Alternatives considered: Combine residual construction and ADF in one function; run ADF
inside the Engle-Granger helper; write statistical results directly from the ADF function.

Risks: Callers remain responsible for providing residuals generated from aligned data and a
documented hedge-ratio method until the full Statistical Testing Agent service is built.
