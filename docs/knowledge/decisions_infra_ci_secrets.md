# Knowledge Decisions: Infrastructure, CI, And Secrets

This shard contains durable decisions about runtime layout, local infrastructure,
Infisical, GitHub Actions, and portability constraints.

## DEC-0002: Keep runtime data outside the Python package

Status: accepted

Decision: Runtime storage, SQLite databases, ApeRAG manifests, vector indexes, reports, logs,
and scratch data must live under top-level ignored directories such as `data/`, not under
`src/stat_arb/`.

Rationale: Package code should stay importable, reviewable, and reproducible without local
runtime artifacts mixed into source directories.

Risks: Scripts must consistently resolve paths from the repository root.

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

## DEC-0015: Run fast Python CI on Ubuntu without external services

Status: accepted

Decision: Add a GitHub Actions workflow on `ubuntu-latest` for push, pull request, and
manual dispatch. The workflow installs dependencies with `uv`, runs user-facing Russian
text checks, secret leak checks, Ruff, and fast unit tests. It intentionally excludes
OmniRoute, Infisical auth, ApeRAG seeding, and other local service checks.

Rationale: The project is developed on Windows but is expected to move to an Ubuntu server.
Running fast CI on Ubuntu catches portability issues early while keeping GitHub Actions
free from local secrets and long-running LLM dependencies.

Alternatives considered: Windows-only CI; running the local PowerShell `check.ps1`; adding
OmniRoute and Infisical integration checks to every push.

Risks: CI does not cover external service readiness or reproducibility checks. Those remain
separate follow-up tasks under the CI section.

## DEC-0057: Enforce core coverage and property/integration smoke in CI

Status: accepted

Decision: CI must run unit tests with coverage over core packages and fail below 70% core
coverage. CI and pre-commit also run `scripts/check_property_integration.ps1`, which keeps
`tests/property` and `tests/integration` active instead of decorative.

Rationale: Task 18.1 promised a 70% coverage gate for core logic, and the repository layout
promised property/integration test locations. Those promises need executable guards, not
just plan text. External service checks remain separate from CI because they require local
Docker state and provider credentials.

Alternatives considered: Keep coverage only in local pytest defaults; leave property tests
inside `tests/unit`; defer integration smoke until the Coordinator exists.

Risks: The integration smoke is local and does not prove live ApeRAG availability. Live
memory readiness remains covered by `scripts/check_memory_health.ps1`.

Update: Task 15.7 adds `tests/integration/test_cli_scripted_workflows.py`, which is covered
by the existing `scripts/check_property_integration.ps1` CI/pre-commit path. The test runs
only local mock data and PowerShell/CLI commands, so it keeps CI free from Docker, ApeRAG,
OmniRoute, Infisical, and exchange credentials while still proving scripted workflow
composition.

## DEC-0024: Close bootstrap tasks 1-4 only after registry reproducibility property test

Status: accepted

Decision: Treat tasks 1-4 as complete only when repository setup, core infrastructure,
domain models, and Data Agent quality validation all have executable checks. Task 2.2 adds
Property 14 by persisting identical experiment payloads into clean SQLite registries and
verifying identical stored snapshots.

Rationale: The Structured Registry is the source of truth for experiment state. Before the
project moves into checkpoint 5 and statistical testing, identical experiment inputs should
produce stable records rather than relying on ad-hoc manual inspection.

Alternatives considered: Skip optional task 2.2; close parent task 2 because the schema
already existed; defer reproducibility checks until final MVP validation.

Risks: This property currently covers the experiment/hypothesis registry boundary only.
Broader reproducibility checks for full experiment artifacts remain later MVP work.

## DEC-0035: Keep Rust behind a measured performance boundary

Status: accepted

Decision: Keep the MVP Python-first and introduce Rust only after profiling identifies a
stable compute hotspot with a documented API boundary, Python reference implementation,
unit/property tests, and benchmark evidence.

Rationale: The current work is still stabilizing domain contracts, ingestion, validation,
registry persistence, memory boundaries, and statistical reference behavior. Adding Rust
before those boundaries settle would add packaging, CI, Windows/Ubuntu build, and FFI
complexity without proven benefit.

Alternatives considered: Start a Rust core immediately; rewrite statistical helpers in
Rust because the final system may need speed; add Rust modules to increase the GitHub
language percentage.

Risks: Python implementations may become slow for large pair universes or backtests. When
profiling proves that, introduce Rust through a narrow optional acceleration package and
use the installed `rust-skills` guidance for Rust code.
