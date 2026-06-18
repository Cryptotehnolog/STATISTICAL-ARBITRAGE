"""Persistence helpers for statistical model-comparison artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from stat_arb.statistical.model_comparison import ModelComparisonReport
from stat_arb.storage.models import Experiment, ReportArtifact


@dataclass(frozen=True)
class StoredModelComparisonArtifact:
    """JSON sidecar and registry artifact for a statistical model-comparison report."""

    artifact: ReportArtifact
    path: Path
    payload: dict[str, object]


def persist_model_comparison_artifact(
    session: Session,
    report: ModelComparisonReport,
    *,
    artifact_root: Path | str,
    experiment_id: str,
) -> StoredModelComparisonArtifact:
    """Persist model-comparison evidence as a JSON sidecar plus registry artifact."""
    experiment = session.get(Experiment, experiment_id)
    if experiment is None:
        raise ValueError(f"experiment is required for model comparison artifact {experiment_id}")

    artifact_dir = Path(artifact_root) / "statistical_model_comparison"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / f"{report.comparison_id}.json"
    payload = report.to_payload()
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    artifact = ReportArtifact(
        experiment_id=experiment_id,
        artifact_type="statistical_model_comparison",
        file_path=str(path),
        format="json",
    )
    session.add(artifact)
    session.flush()
    return StoredModelComparisonArtifact(artifact=artifact, path=path, payload=payload)
