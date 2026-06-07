"""Unit tests for Statistical Testing Agent service boundary."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from stat_arb.agents import StatisticalTestingInput, run_statistical_testing
from stat_arb.memory import MemoryWriteRequest
from stat_arb.storage import Base, DataQualityReportRecord, Dataset, Hypothesis
from stat_arb.storage.models import StatisticalTestResult as StoredStatisticalTestResult


class FakeMemoryService:
    """Fake Memory Agent service that records write requests."""

    def __init__(self) -> None:
        self.requests: list[MemoryWriteRequest] = []

    def write(self, request: MemoryWriteRequest) -> object:
        self.requests.append(request)
        return object()


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


def test_run_statistical_testing_persists_registry_result_and_memory(session: Session) -> None:
    """Service should write structured metrics to registry and concise summary to memory."""
    hypothesis_id, dataset_a_id, dataset_b_id = _seed_prerequisites(session, with_quality=True)
    prices_a, prices_b, timestamps = _cointegrated_pair()
    memory = FakeMemoryService()

    result = run_statistical_testing(
        StatisticalTestingInput(
            hypothesis_id=hypothesis_id,
            dataset_a_id=dataset_a_id,
            dataset_b_id=dataset_b_id,
            prices_a=prices_a,
            prices_b=prices_b,
            aligned_timestamps=timestamps,
            train_fraction=0.7,
            alpha=0.05,
            adf_regression="c",
            adf_autolag="AIC",
            periods_per_day=96.0,
            regime_window=60,
            regime_mean_shift_threshold=3.0,
            regime_volatility_ratio_threshold=2.5,
        ),
        session=session,
        memory_service=memory,
    )

    stored = session.query(StoredStatisticalTestResult).one()
    assert result.domain_result.passed is True
    assert result.stored_result.test_id == stored.test_id
    assert stored.dataset_a_id == str(dataset_a_id)
    assert stored.dataset_b_id == str(dataset_b_id)
    assert stored.train_end < stored.test_start
    assert stored.passed is True
    assert result.memory_written is True
    assert len(memory.requests) == 1
    assert memory.requests[0].registry_reference == f"registry:statistical_test_results/{stored.test_id}"
    assert "Structured test metrics are stored in the registry" in memory.requests[0].body


def test_run_statistical_testing_requires_passed_quality_reports(session: Session) -> None:
    """Service must not test pairs before both datasets have passed quality reports."""
    hypothesis_id, dataset_a_id, dataset_b_id = _seed_prerequisites(session, with_quality=False)
    prices_a, prices_b, timestamps = _cointegrated_pair()

    with pytest.raises(ValueError, match="passed data quality report"):
        run_statistical_testing(
            StatisticalTestingInput(
                hypothesis_id=hypothesis_id,
                dataset_a_id=dataset_a_id,
                dataset_b_id=dataset_b_id,
                prices_a=prices_a,
                prices_b=prices_b,
                aligned_timestamps=timestamps,
                train_fraction=0.7,
                alpha=0.05,
                adf_regression="c",
                adf_autolag="AIC",
                periods_per_day=96.0,
                regime_window=60,
                regime_mean_shift_threshold=3.0,
                regime_volatility_ratio_threshold=2.5,
            ),
            session=session,
        )

    assert session.query(StoredStatisticalTestResult).count() == 0


def test_run_statistical_testing_validates_chronological_inputs(session: Session) -> None:
    """Service should reject timestamp/order issues before registry writes."""
    hypothesis_id, dataset_a_id, dataset_b_id = _seed_prerequisites(session, with_quality=True)
    prices_a, prices_b, timestamps = _cointegrated_pair()
    timestamps = list(timestamps)
    timestamps[10] = timestamps[9]

    with pytest.raises(ValueError, match="strictly increasing"):
        run_statistical_testing(
            StatisticalTestingInput(
                hypothesis_id=hypothesis_id,
                dataset_a_id=dataset_a_id,
                dataset_b_id=dataset_b_id,
                prices_a=prices_a,
                prices_b=prices_b,
                aligned_timestamps=timestamps,
                train_fraction=0.7,
                alpha=0.05,
                adf_regression="c",
                adf_autolag="AIC",
                periods_per_day=96.0,
                regime_window=60,
                regime_mean_shift_threshold=3.0,
                regime_volatility_ratio_threshold=2.5,
            ),
            session=session,
        )


def _seed_prerequisites(
    session: Session,
    *,
    with_quality: bool,
) -> tuple[object, object, object]:
    hypothesis_id = uuid4()
    dataset_a_id = uuid4()
    dataset_b_id = uuid4()
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 3, tzinfo=UTC)
    hypothesis = Hypothesis(
        hypothesis_id=str(hypothesis_id),
        asset_a="AAA",
        asset_b="BBB",
        rationale="Synthetic pair",
        source="unit-test",
        created_by="pytest",
    )
    dataset_a = Dataset(
        dataset_id=str(dataset_a_id),
        symbol="AAA",
        source="unit-test",
        timeframe="15m",
        start_date=start,
        end_date=end,
        bar_count=240,
        adjustment_mode="none",
        file_path="/tmp/a.parquet",
    )
    dataset_b = Dataset(
        dataset_id=str(dataset_b_id),
        symbol="BBB",
        source="unit-test",
        timeframe="15m",
        start_date=start,
        end_date=end,
        bar_count=240,
        adjustment_mode="none",
        file_path="/tmp/b.parquet",
    )
    session.add_all([hypothesis, dataset_a, dataset_b])
    if with_quality:
        session.add_all(
            [
                _quality_report(dataset_a_id, "AAA", start, end),
                _quality_report(dataset_b_id, "BBB", start, end),
            ]
        )
    session.commit()
    return hypothesis_id, dataset_a_id, dataset_b_id


def _quality_report(dataset_id: object, symbol: str, start: datetime, end: datetime) -> DataQualityReportRecord:
    return DataQualityReportRecord(
        report_id=str(uuid4()),
        dataset_id=str(dataset_id),
        symbol=symbol,
        source="unit-test",
        timeframe="15m",
        start_date=start,
        end_date=end,
        bar_count=240,
        expected_bar_count=240,
        timezone_normalized=True,
        alignment_score=1.0,
        quality_score=1.0,
        passed=True,
        issues=[],
        report_path=f"/tmp/{symbol}-quality.json",
        generated_at=start,
    )


def _cointegrated_pair() -> tuple[np.ndarray, np.ndarray, tuple[datetime, ...]]:
    rng = np.random.default_rng(42)
    observations = 240
    asset_b = np.cumsum(rng.normal(size=observations)) + 100.0
    residuals = np.zeros(observations)
    shocks = rng.normal(scale=0.2, size=observations)
    for index in range(1, observations):
        residuals[index] = 0.65 * residuals[index - 1] + shocks[index]
    asset_a = 1.4 * asset_b + residuals
    start = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=15 * index) for index in range(observations))
    return asset_a, asset_b, timestamps
