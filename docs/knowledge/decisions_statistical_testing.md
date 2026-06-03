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

## DEC-0030: Keep statistical property tests bounded

Status: accepted

Decision: Cover synthetic cointegration, stationary residual detection, and half-life
formula recovery with bounded Hypothesis tests under `tests/unit`, using small
`max_examples` counts.

Rationale: `statsmodels` tests are materially slower than pure data-shape validation.
Property tests are still valuable for numerical boundaries, but they must not make every
local commit or GitHub Actions run too slow for routine development.

Alternatives considered: Put heavy property tests in the fast unit suite; skip optional
property tests; move all statistical property tests to a later CI-only workflow.

Risks: The bounded suite is a smoke-level property baseline, not a full statistical
simulation campaign. Stochastic half-life accuracy is intentionally left to a separate slow
workflow because noisy OU simulations can be flaky near the 20% tolerance boundary.

## DEC-0031: Estimate hedge ratio with a pure OLS helper

Status: accepted

Decision: Implement hedge-ratio estimation under `stat_arb.statistical` as a pure OLS
helper that regresses dependent prices on independent prices and returns hedge ratio,
intercept, R-squared, and observation count.

Rationale: Hedge-ratio estimation is reused by spread construction, ADF residual testing,
z-score signals, and later backtests. Keeping it pure avoids coupling the statistical math
to registry persistence or ApeRAG writes before the full Statistical Testing Agent service
exists.

Alternatives considered: Estimate hedge ratio inside the cointegration helper; use ad-hoc
NumPy formulas without regression metadata; defer hedge ratio until backtesting.

Risks: The helper does not decide which asset should be dependent versus independent. The
future Statistical Testing Agent workflow must document and persist that pair orientation.

## DEC-0032: Estimate half-life from residual mean reversion

Status: accepted

Decision: Implement half-life estimation under `stat_arb.statistical` as a pure helper that
fits `delta_residual ~ lagged_residual`, derives the AR(1) phi value, and returns half-life
in both periods and days.

Rationale: Half-life is a statistical property of the spread/residual series and should be
computed before signal construction and backtesting. Keeping the helper pure allows
synthetic OU-style tests and avoids registry or ApeRAG coupling before service integration.

Alternatives considered: Estimate half-life directly inside z-score signal construction;
store only the raw regression beta; defer half-life until the Backtest Agent.

Risks: Half-life estimates are sensitive to sample length and residual construction. The
future Statistical Testing Agent should persist method assumptions and reject non-positive
mean-reversion estimates explicitly.

## DEC-0033: Construct rolling Z-scores as a pure signal helper

Status: accepted

Decision: Implement rolling Z-score construction under `stat_arb.statistical` as a pure
helper that accepts finite one-dimensional spread residuals, requires a full rolling
window, and returns typed arrays for Z-scores, rolling mean, and rolling standard
deviation.

Rationale: Z-scores are the boundary between statistical validation and later trading
signal generation. Keeping them pure makes the calculation easy to test and prevents early
coupling to the registry, ApeRAG, or backtesting services.

Alternatives considered: Build Z-score logic directly into the Backtest Agent; allow
partial-window early signals; persist signal rows from the helper itself.

Risks: The helper does not decide entry/exit thresholds or trading direction. Those rules
belong to later signal/backtest tasks and must preserve the pair orientation established by
hedge-ratio estimation.

## DEC-0036: Detect regime changes before backtest signal generation

Status: accepted

Decision: Implement regime change detection under `stat_arb.statistical` as a pure helper
that compares adjacent rolling windows for mean shifts and volatility shifts, returning
typed structural break candidates.

Rationale: Pair strategies can pass cointegration and stationarity checks on one segment
while becoming unstable after a structural break. Regime detection belongs before signal
generation and backtesting so the Statistical Testing Agent can flag unstable pairs rather
than feeding them blindly into entry/exit rules.

Alternatives considered: Skip regime checks until the Critic Agent; implement a full Chow
test immediately; put regime logic inside the backtest engine.

Risks: Rolling-statistics detection is a pragmatic first screen, not a complete structural
break test suite. Later services should persist detected breakpoints and can add Chow-style
or model-based tests when pair testing workflows are mature.
