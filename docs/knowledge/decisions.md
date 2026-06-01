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

## DEC-0004: Use no-op LLM fallback until a project LLM provider is configured

Status: accepted

Decision: Provide a local no-op `llm_model_func` so LightRAG can initialize and store vector
chunks without requiring API keys or a network LLM.

Rationale: The current LightRAG build requires `llm_model_func` to be callable during
initialization even though the signature allows `None`. A no-op fallback keeps local
knowledge seeding available while the project has no configured LLM provider.

Alternatives considered: Block all LightRAG writes until an LLM provider exists; wire a
cloud LLM immediately.

Risks: Entity and relationship extraction remains empty with the no-op fallback, so this is
vector memory only until a real LLM provider is configured.

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
