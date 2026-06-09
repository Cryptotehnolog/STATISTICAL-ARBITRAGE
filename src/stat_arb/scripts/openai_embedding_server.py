"""Small OpenAI-compatible embedding server for local ApeRAG indexing."""

from __future__ import annotations

import os
import time
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

MODEL_NAME = os.getenv("STAT_ARB_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
LOCAL_FILES_ONLY = os.getenv("STAT_ARB_EMBEDDING_LOCAL_FILES_ONLY", "true").lower() in {
    "1",
    "true",
    "yes",
}

app = FastAPI(title="Stat Arb local embeddings", version="0.1.0")
_model: SentenceTransformer | None = None


class EmbeddingRequest(BaseModel):
    model: str = Field(default=MODEL_NAME)
    input: str | list[str]


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME, local_files_only=LOCAL_FILES_ONLY)
    return _model


def _normalize_input(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        return [value]
    if not value:
        raise HTTPException(status_code=400, detail="input must not be empty")
    return [text if text and text.strip() else " " for text in value]


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "local_files_only": LOCAL_FILES_ONLY,
    }


@app.get("/v1/models")
def models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_NAME,
                "object": "model",
                "owned_by": "stat-arb-local",
            }
        ],
    }


@app.post("/v1/embeddings")
def embeddings(request: EmbeddingRequest) -> dict[str, Any]:
    texts = _normalize_input(request.input)
    model = _get_model()
    vectors = np.asarray(model.encode(texts, normalize_embeddings=True), dtype=float).tolist()

    return {
        "object": "list",
        "model": MODEL_NAME,
        "data": [
            {
                "object": "embedding",
                "index": index,
                "embedding": vector,
            }
            for index, vector in enumerate(vectors)
        ],
        "usage": {
            "prompt_tokens": sum(len(text.split()) for text in texts),
            "total_tokens": sum(len(text.split()) for text in texts),
        },
        "created": int(time.time()),
    }
