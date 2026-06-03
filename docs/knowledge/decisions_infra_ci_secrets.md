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

Risks: CI does not yet cover external service readiness, property tests, or reproducibility
checks. Those remain separate follow-up tasks under the CI section.
