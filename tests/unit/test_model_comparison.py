"""Unit tests for explicit statistical model-comparison benchmark harness."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from stat_arb.statistical import (
    ModelComparisonMethod,
    ModelComparisonScenario,
    compare_cointegration_models,
)
from stat_arb.storage import Base, Experiment, Hypothesis, ReportArtifact
from stat_arb.storage.model_comparison import persist_model_comparison_artifact


@pytest.fixture
def session() -> Session:
    """Create an in-memory registry session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db_session = session_factory()
    try:
        yield db_session
    finally:
        db_session.close()
        engine.dispose()


def test_model_comparison_requires_explicit_engle_granger_baseline() -> None:
    """Benchmark scenarios must keep Engle-Granger as the explicit baseline."""
    asset_a, asset_b = _cointegrated_pair()

    with pytest.raises(ValueError, match="exactly one baseline"):
        compare_cointegration_models(
            asset_a,
            asset_b,
            scenarios=(
                ModelComparisonScenario(
                    name="kalman-candidate",
                    method=ModelComparisonMethod.KALMAN,
                    alpha=0.05,
                    parameters={"state_noise": "manual-review-required"},
                    is_baseline=False,
                ),
            ),
        )

    with pytest.raises(ValueError, match="baseline must use engle_granger"):
        compare_cointegration_models(
            asset_a,
            asset_b,
            scenarios=(
                ModelComparisonScenario(
                    name="kalman-baseline",
                    method=ModelComparisonMethod.KALMAN,
                    alpha=0.05,
                    parameters={"state_noise": "manual-review-required"},
                    is_baseline=True,
                ),
            ),
        )


def test_model_comparison_records_candidates_without_promotion_decision() -> None:
    """Alternative methods should be benchmark evidence, not an approval signal."""
    asset_a, asset_b = _cointegrated_pair()

    report = compare_cointegration_models(
        asset_a,
        asset_b,
        scenarios=(
            ModelComparisonScenario(
                name="engle-granger-baseline",
                method=ModelComparisonMethod.ENGLE_GRANGER,
                alpha=0.05,
                parameters={"multiple_testing_method": "none"},
                is_baseline=True,
            ),
            ModelComparisonScenario(
                name="johansen-candidate",
                method=ModelComparisonMethod.JOHANSEN,
                alpha=0.05,
                parameters={"det_order": 0, "k_ar_diff": 1},
                is_baseline=False,
            ),
            ModelComparisonScenario(
                name="phillips-perron-candidate",
                method=ModelComparisonMethod.PHILLIPS_PERRON,
                alpha=0.05,
                parameters={"residual_source": "engle_granger_baseline"},
                is_baseline=False,
            ),
        ),
        dataset_ids=("dataset-a", "dataset-b"),
        hypothesis_id="hypothesis-1",
    )

    assert report.hypothesis_id == "hypothesis-1"
    assert report.dataset_ids == ("dataset-a", "dataset-b")
    assert report.baseline_method == ModelComparisonMethod.ENGLE_GRANGER
    assert report.results[0].status == "completed"
    assert report.results[0].method == ModelComparisonMethod.ENGLE_GRANGER
    assert report.results[0].p_value is not None
    assert report.results[0].passed is True
    johansen = report.results[1]
    phillips_perron = report.results[2]
    assert johansen.status == "completed"
    assert johansen.method == ModelComparisonMethod.JOHANSEN
    assert johansen.p_value is None
    assert johansen.passed is True
    assert johansen.details["trace_statistic_rank_0"] == pytest.approx(johansen.statistic)
    assert johansen.details["critical_value"] > 0.0
    assert johansen.details["critical_value_level"] == "95%"
    assert phillips_perron.status == "not_implemented"
    assert phillips_perron.passed is None
    assert report.promotion_decision is None
    assert "Coordinator/Critic" in report.decision_boundary


def test_johansen_scenario_requires_explicit_supported_parameters() -> None:
    """Johansen scenarios should reject hidden lag/deterministic assumptions."""
    asset_a, asset_b = _cointegrated_pair()

    for parameters, error in (
        ({"det_order": 0}, "k_ar_diff"),
        ({"k_ar_diff": 1}, "det_order"),
        ({"det_order": 0, "k_ar_diff": -1}, "k_ar_diff"),
    ):
        with pytest.raises(ValueError, match=error):
            compare_cointegration_models(
                asset_a,
                asset_b,
                scenarios=(
                    ModelComparisonScenario(
                        name="engle-granger-baseline",
                        method=ModelComparisonMethod.ENGLE_GRANGER,
                        alpha=0.05,
                        parameters={"multiple_testing_method": "none"},
                        is_baseline=True,
                    ),
                    ModelComparisonScenario(
                        name="johansen-candidate",
                        method=ModelComparisonMethod.JOHANSEN,
                        alpha=0.05,
                        parameters=parameters,
                        is_baseline=False,
                    ),
                ),
            )

    with pytest.raises(ValueError, match="supported Johansen alpha"):
        compare_cointegration_models(
            asset_a,
            asset_b,
            scenarios=(
                ModelComparisonScenario(
                    name="engle-granger-baseline",
                    method=ModelComparisonMethod.ENGLE_GRANGER,
                    alpha=0.05,
                    parameters={"multiple_testing_method": "none"},
                    is_baseline=True,
                ),
                ModelComparisonScenario(
                    name="johansen-candidate",
                    method=ModelComparisonMethod.JOHANSEN,
                    alpha=0.07,
                    parameters={"det_order": 0, "k_ar_diff": 1},
                    is_baseline=False,
                ),
            ),
        )


def test_model_comparison_rejects_hidden_or_unserializable_scenario_config() -> None:
    """Scenario parameters should be explicit and artifact-serializable."""
    with pytest.raises(ValueError, match="name"):
        ModelComparisonScenario(
            name=" ",
            method=ModelComparisonMethod.ENGLE_GRANGER,
            alpha=0.05,
            parameters={},
            is_baseline=True,
        )

    with pytest.raises(ValueError, match="alpha"):
        ModelComparisonScenario(
            name="engle-granger",
            method=ModelComparisonMethod.ENGLE_GRANGER,
            alpha=1.0,
            parameters={},
            is_baseline=True,
        )

    with pytest.raises(ValueError, match="JSON-serializable"):
        ModelComparisonScenario(
            name="engle-granger",
            method=ModelComparisonMethod.ENGLE_GRANGER,
            alpha=0.05,
            parameters={"bad": object()},
            is_baseline=True,
        )


def test_persist_model_comparison_artifact_writes_json_sidecar_and_registry(
    session: Session,
    tmp_path: Path,
) -> None:
    """Model-comparison evidence should be durable as a JSON artifact."""
    experiment_id = _seed_experiment(session)
    report = compare_cointegration_models(
        *_cointegrated_pair(),
        scenarios=(
            ModelComparisonScenario(
                name="engle-granger-baseline",
                method=ModelComparisonMethod.ENGLE_GRANGER,
                alpha=0.05,
                parameters={"multiple_testing_method": "none"},
                is_baseline=True,
            ),
        ),
        dataset_ids=("dataset-a", "dataset-b"),
        hypothesis_id="hypothesis-1",
    )

    stored = persist_model_comparison_artifact(
        session,
        report,
        artifact_root=tmp_path,
        experiment_id=experiment_id,
    )

    assert stored.path.exists()
    assert stored.payload["promotion_decision"] is None
    assert stored.payload["decision_boundary"].startswith("Model comparison")
    assert stored.payload["results"][0]["details"]["critical_values"]
    artifact = session.query(ReportArtifact).one()
    assert artifact.artifact_type == "statistical_model_comparison"
    assert artifact.format == "json"
    assert artifact.file_path == str(stored.path)


def _cointegrated_pair() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(420)
    observations = 240
    asset_b = np.cumsum(rng.normal(size=observations)) + 100.0
    residuals = rng.normal(scale=0.07, size=observations)
    asset_a = 1.35 * asset_b + residuals
    return asset_a, asset_b


def _seed_experiment(session: Session) -> str:
    hypothesis_id = "hypothesis-1"
    experiment_id = str(uuid4())
    session.add(
        Hypothesis(
            hypothesis_id=hypothesis_id,
            asset_a="AAA",
            asset_b="BBB",
            rationale="Synthetic pair",
            source="unit-test",
            created_by="pytest",
        )
    )
    session.add(
        Experiment(
            experiment_id=experiment_id,
            hypothesis_id=hypothesis_id,
            status="statistical_testing",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
    )
    session.commit()
    return experiment_id
