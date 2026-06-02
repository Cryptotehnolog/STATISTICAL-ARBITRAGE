# Future Ideas

This file collects ideas discovered during development that should be considered later but
should not distract from the current task. Codex should append durable ideas here when they
come up during implementation or review, then the LightRAG seed command will ingest them.

## IDEA-0001: Chroma compatibility spike

Status: proposed

Idea: Verify whether a newer or differently installed LightRAG build supports
`ChromaVectorDBStorage`, what dependencies are required, and whether it can run embedded
without Docker for the local MVP.

Why later: FAISS currently works and keeps the MVP small. Chroma should be adopted only if
it provides a clear operational or retrieval benefit.

## IDEA-0002: Automate knowledge seed after successful task commits

Status: proposed

Idea: Add an optional local workflow that runs the knowledge seed command after commits that
touch `README.md`, `.kiro/specs/`, `docs/`, or architecture-relevant source files.

Why later: The seed command writes local runtime state and may load embeddings, so it should
remain opt-in until the workflow is proven stable and fast enough.

## IDEA-0003: Add quality checks for LightRAG graph extraction

Status: proposed

Idea: Add a smoke test that seeds a tiny document through Ollama and asserts that LightRAG
extracts at least one entity or relationship.

Why later: Provider wiring exists, but graph extraction quality should be validated
separately from the fast unit baseline because it depends on a local Ollama service and
model runtime.
