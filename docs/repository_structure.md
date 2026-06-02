# Repository Structure

This repository uses a local-first Python package layout for the Statistical Arbitrage research platform.

## Top-Level Directories

- `.kiro/specs/` contains planning specifications and task breakdowns. These are project source artifacts.
- `.kiro/skills/` is a local Kiro tool/cache directory and is intentionally ignored.
- `data/` contains runtime data, local databases, LightRAG stores, vector indexes, and test scratch data. It is intentionally ignored.
- `docs/` contains project documentation that should be committed.
- `docs/knowledge/` contains curated decisions and future ideas that are seeded into LightRAG.
- `scripts/` contains developer and operator scripts, mostly PowerShell wrappers for local checks and workflows.
- `src/stat_arb/` contains importable Python package code.
- `tests/` contains automated tests split by test type.

## Python Package Layout

- `src/stat_arb/agents/` will contain agent implementations.
- `src/stat_arb/backtest/` will contain backtesting engines and cost attribution logic.
- `src/stat_arb/cli/` will contain CLI command wiring.
- `src/stat_arb/dashboard/` will contain dashboard code.
- `src/stat_arb/memory/` contains LightRAG configuration and client code.
- `src/stat_arb/models/` is reserved for future shared package models if needed.
- `src/stat_arb/scripts/` contains Python module entrypoints that can be run with `python -m`.
- `src/stat_arb/statistical/` will contain statistical testing logic.
- `src/stat_arb/storage/` contains the Structured Registry database layer. `storage/models.py` is SQLAlchemy ORM, not domain/Pydantic models.
- `src/stat_arb/utils/` contains shared utilities.

## Model Boundaries

- SQLAlchemy persistence models live in `src/stat_arb/storage/models.py`.
- Future Pydantic/domain models should live in `src/stat_arb/domain/` when task `3.1` starts.
- Runtime data must not live under `src/`; package code should stay importable and reproducible without local caches.

## Test Layout

- `tests/unit/` contains fast isolated unit tests.
- `tests/integration/` contains integration tests that may touch local services or heavier dependencies.
- `tests/property/` contains property-based tests.
- Tests marked `slow` are excluded from the default unit baseline.

## Local Checks

- `scripts/check_unit.ps1` runs the fast unit baseline.
- `scripts/check.ps1` runs Ruff plus the fast unit baseline and should be used before commits.
- `scripts/seed_lightrag.ps1` seeds changed curated project knowledge into local LightRAG storage.
- `scripts/smoke_lightrag_omniroute.ps1` runs a small isolated LightRAG + OmniRoute graph extraction smoke test.
- `scripts/benchmark_lightrag_omniroute.ps1` compares OmniRoute models on the same LightRAG extraction document.
