"""Experiment reproducibility snapshots for backtests."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ReproducibilityManifest:
    """Immutable metadata needed to rerun and audit one experiment."""

    git_commit_hash: str
    config_hash: str
    dataset_ids: tuple[str, ...]
    random_seed: int | None
    execution_command: tuple[str, ...]
    run_timestamp: datetime
    lock_file_hash: str


def create_reproducibility_manifest(
    *,
    git_commit_hash: str,
    config_components: Mapping[str, Any],
    dataset_ids: Sequence[str],
    random_seed: int | None,
    execution_command: Sequence[str],
    run_timestamp: datetime,
    lock_file_path: str | Path,
) -> ReproducibilityManifest:
    """Create reproducibility metadata from explicit experiment inputs."""
    return ReproducibilityManifest(
        git_commit_hash=_validate_git_commit_hash(git_commit_hash),
        config_hash=calculate_config_hash(config_components),
        dataset_ids=_validate_dataset_ids(dataset_ids),
        random_seed=_validate_random_seed(random_seed),
        execution_command=_validate_execution_command(execution_command),
        run_timestamp=_validate_run_timestamp(run_timestamp),
        lock_file_hash=hash_file(lock_file_path),
    )


def calculate_config_hash(config_components: Mapping[str, Any]) -> str:
    """Return a stable SHA-256 hash for explicit experiment configuration."""
    if not config_components:
        raise ValueError("config_components must not be empty")
    canonical = json.dumps(
        _to_canonical_json_value(config_components),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def hash_file(path: str | Path) -> str:
    """Return SHA-256 hash for a dependency lock or other reproducibility file."""
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"lock file not found: {file_path}")
    digest = hashlib.sha256()
    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _to_canonical_json_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _to_canonical_json_value(asdict(value))
    if isinstance(value, Mapping):
        return {
            str(key): _to_canonical_json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_to_canonical_json_value(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float):
        if not np.isfinite(value):
            raise ValueError("config_components must not contain non-finite floats")
        return value
    if value is None or isinstance(value, bool | int | str):
        return value
    raise TypeError(f"unsupported config component type: {type(value).__name__}")


def _validate_git_commit_hash(value: str) -> str:
    commit = value.strip()
    if not 7 <= len(commit) <= 40:
        raise ValueError("git_commit_hash must be 7 to 40 hexadecimal characters")
    if any(character not in "0123456789abcdefABCDEF" for character in commit):
        raise ValueError("git_commit_hash must be hexadecimal")
    return commit.lower()


def _validate_dataset_ids(values: Sequence[str]) -> tuple[str, ...]:
    dataset_ids = tuple(value.strip() for value in values)
    if not dataset_ids:
        raise ValueError("dataset_ids must not be empty")
    if any(not value for value in dataset_ids):
        raise ValueError("dataset_ids must not contain empty values")
    if len(set(dataset_ids)) != len(dataset_ids):
        raise ValueError("dataset_ids must be unique")
    return dataset_ids


def _validate_random_seed(value: int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("random_seed must be an integer or None")
    if value < 0:
        raise ValueError("random_seed must be non-negative")
    return value


def _validate_execution_command(values: Sequence[str]) -> tuple[str, ...]:
    command = tuple(value.strip() for value in values)
    if not command:
        raise ValueError("execution_command must not be empty")
    if any(not value for value in command):
        raise ValueError("execution_command must not contain empty values")
    return command


def _validate_run_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("run_timestamp must be timezone-aware")
    return value
