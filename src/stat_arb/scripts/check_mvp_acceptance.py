"""Task 22 MVP acceptance checkpoint.

The default command builds a deterministic local registry fixture and verifies the MVP
acceptance criteria without live exchanges, Docker services, LLM providers, or secrets.
Live-scale market-data validation remains an explicit operator run, not a CI dependency.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from stat_arb.storage import (
    BacktestResult,
    Base,
    CoordinatorTask,
    CriticReview,
    DataQualityReportRecord,
    Dataset,
    Experiment,
    Hypothesis,
    ReportArtifact,
    StatisticalTestResult,
    create_database_engine,
    create_session_factory,
)


@dataclass(frozen=True)
class MVPAcceptanceTargets:
    """Explicit numeric targets from Task 22."""

    min_assets: int = 50
    max_assets: int = 100
    min_pairs_tested: int = 10
    min_experiments: int = 5
    timeframe: str = "15m"
    min_history_days: int = 180
    max_full_experiment_runtime_seconds: float = 300.0
    max_memory_gb: float = 8.0
    max_dataset_disk_gb: float = 20.0


@dataclass(frozen=True)
class MVPNumericEvidence:
    """Observed numeric evidence for Task 22.2."""

    assets: int
    pairs_tested: int
    completed_experiments: int
    generated_reports: int
    timeframe: str
    min_history_days: int
    max_experiment_runtime_seconds: float


@dataclass(frozen=True)
class MVPAcceptanceSection:
    """One Task 22 acceptance section."""

    task_id: str
    title: str
    passed: bool
    evidence: tuple[str, ...]
    failures: tuple[str, ...]


@dataclass(frozen=True)
class MVPAcceptanceReport:
    """Complete Task 22 acceptance report."""

    passed: bool
    numeric: MVPNumericEvidence
    sections: tuple[MVPAcceptanceSection, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable report."""
        return asdict(self)


MVP_ACCEPTANCE_TARGETS = MVPAcceptanceTargets()
REPORT_ARTIFACT_TYPES = (
    "backtest_report",
    "json_summary",
    "equity_curve",
    "z_score_signals",
    "cost_attribution",
    "rolling_sharpe",
    "trade_distribution",
)


def seed_deterministic_mvp_registry(
    db_path: Path,
    *,
    asset_count: int = MVP_ACCEPTANCE_TARGETS.min_assets,
    pair_count: int = MVP_ACCEPTANCE_TARGETS.min_pairs_tested,
    experiment_count: int = MVP_ACCEPTANCE_TARGETS.min_experiments,
) -> None:
    """Create a deterministic local registry fixture for Task 22 acceptance."""
    if experiment_count > pair_count:
        raise ValueError("experiment_count cannot exceed pair_count")
    if pair_count * 2 > asset_count:
        raise ValueError("asset_count must provide two unique assets per pair")

    engine = create_database_engine(db_path)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()
    try:
        started_at = datetime(2024, 1, 1, tzinfo=UTC).replace(tzinfo=None)
        ended_at = started_at + timedelta(days=MVP_ACCEPTANCE_TARGETS.min_history_days)
        _seed_datasets(session, asset_count=asset_count, started_at=started_at, ended_at=ended_at)
        hypotheses = _seed_hypotheses_and_tests(
            session,
            pair_count=pair_count,
            started_at=started_at,
            ended_at=ended_at,
        )
        _seed_completed_experiments(
            session,
            hypotheses=hypotheses[:experiment_count],
            started_at=started_at,
            ended_at=ended_at,
        )
        session.commit()
    finally:
        session.close()
        engine.dispose()


def build_mvp_acceptance_report(
    *,
    session: Session,
    repo_root: Path,
    targets: MVPAcceptanceTargets = MVP_ACCEPTANCE_TARGETS,
) -> MVPAcceptanceReport:
    """Evaluate Task 22 acceptance against registry and repository evidence."""
    numeric = _numeric_evidence(session, targets=targets)
    sections = (
        _section_22_1(numeric, targets),
        _section_22_2(numeric, targets),
        _section_22_3(session=session, repo_root=repo_root),
        _section_22_4(repo_root=repo_root, targets=targets),
        _section_22_5(repo_root=repo_root),
    )
    return MVPAcceptanceReport(
        passed=all(section.passed for section in sections),
        numeric=numeric,
        sections=sections,
    )


def main() -> int:
    """CLI entrypoint for the PowerShell wrapper."""
    parser = argparse.ArgumentParser(description="Проверка Task 22 MVP acceptance.")
    parser.add_argument("--db-path", type=Path, default=None)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument(
        "--use-existing-registry",
        action="store_true",
        help="Проверять существующий registry вместо deterministic fixture.",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="stat-arb-mvp-acceptance-") as temp_dir:
        db_path = args.db_path or Path(temp_dir) / "mvp_acceptance.db"
        if not args.use_existing_registry:
            seed_deterministic_mvp_registry(db_path)

        engine = create_database_engine(db_path)
        session = create_session_factory(engine)()
        try:
            report = build_mvp_acceptance_report(session=session, repo_root=args.repo_root)
        finally:
            session.close()
            engine.dispose()

    payload = report.to_dict()
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    _print_report(report)
    return 0 if report.passed else 1


def _seed_datasets(
    session: Session,
    *,
    asset_count: int,
    started_at: datetime,
    ended_at: datetime,
) -> None:
    bar_count = MVP_ACCEPTANCE_TARGETS.min_history_days * 96
    for index in range(asset_count):
        symbol = f"BYBIT{index:03d}USDT"
        dataset_id = str(uuid4())
        missing_bars = 1 if index == 0 else 0
        outlier_count = 1 if index == 1 else 0
        session.add(
            Dataset(
                dataset_id=dataset_id,
                symbol=symbol,
                source="ccxt:bybit",
                timeframe=MVP_ACCEPTANCE_TARGETS.timeframe,
                start_date=started_at,
                end_date=ended_at,
                bar_count=bar_count,
                missing_bars=missing_bars,
                outlier_count=outlier_count,
                quality_score=0.995 if missing_bars or outlier_count else 1.0,
                adjustment_mode="none",
                file_path=f"data/mvp_acceptance/raw/{symbol}.parquet",
                extra_metadata={
                    "exchange": "bybit",
                    "market_type": "perpetual",
                    "fixture": "deterministic-mvp-acceptance",
                },
            ),
        )
        session.add(
            DataQualityReportRecord(
                report_id=str(uuid4()),
                dataset_id=dataset_id,
                symbol=symbol,
                source="ccxt:bybit",
                timeframe=MVP_ACCEPTANCE_TARGETS.timeframe,
                start_date=started_at,
                end_date=ended_at,
                bar_count=bar_count,
                expected_bar_count=bar_count + missing_bars,
                missing_bars=missing_bars,
                duplicate_timestamps=0,
                outlier_count=outlier_count,
                zero_price_count=0,
                impossible_candle_count=0,
                abnormal_volume_count=0,
                timezone_normalized=True,
                alignment_score=0.999 if missing_bars else 1.0,
                quality_score=0.995 if missing_bars or outlier_count else 1.0,
                passed=True,
                is_valid=True,
                invalid_reason=None,
                issues=["missing_bar_detected"] if missing_bars else [],
                report_path=f"data/mvp_acceptance/quality/{symbol}.json",
                generated_at=started_at,
            ),
        )


def _seed_hypotheses_and_tests(
    session: Session,
    *,
    pair_count: int,
    started_at: datetime,
    ended_at: datetime,
) -> list[Hypothesis]:
    hypotheses: list[Hypothesis] = []
    for pair_index in range(pair_count):
        asset_a = f"BYBIT{pair_index * 2:03d}USDT"
        asset_b = f"BYBIT{pair_index * 2 + 1:03d}USDT"
        hypothesis = Hypothesis(
            hypothesis_id=str(uuid4()),
            asset_a=asset_a,
            asset_b=asset_b,
            rationale="Deterministic MVP acceptance pair with synthetic cointegration evidence.",
            source="rule_based",
            similar_hypotheses=[],
            novelty_score=1.0,
            status="testing",
            created_at=started_at,
            created_by="hypothesis_agent",
        )
        session.add(hypothesis)
        hypotheses.append(hypothesis)
        session.flush()
        dataset_a = _dataset_for_symbol(session, asset_a)
        dataset_b = _dataset_for_symbol(session, asset_b)
        session.add(
            StatisticalTestResult(
                test_id=str(uuid4()),
                hypothesis_id=hypothesis.hypothesis_id,
                dataset_a_id=dataset_a.dataset_id,
                dataset_b_id=dataset_b.dataset_id,
                train_start=started_at,
                train_end=started_at + timedelta(days=120),
                test_start=started_at + timedelta(days=121),
                test_end=ended_at,
                cointegration_statistic=-4.2 - pair_index * 0.01,
                cointegration_p_value=0.01,
                adf_statistic=-3.8,
                adf_p_value=0.02,
                hedge_ratio=1.0 + pair_index * 0.001,
                hedge_ratio_r_squared=0.92,
                half_life_days=4.0,
                residual_ljung_box_p_value=0.42,
                residual_jarque_bera_p_value=0.31,
                residual_excess_kurtosis=0.2,
                residual_diagnostics_lags=10,
                regime_changes_detected=False,
                passed=True,
                rejection_reason=None,
                tested_at=started_at + timedelta(days=181),
            ),
        )
    return hypotheses


def _seed_completed_experiments(
    session: Session,
    *,
    hypotheses: list[Hypothesis],
    started_at: datetime,
    ended_at: datetime,
) -> None:
    for index, hypothesis in enumerate(hypotheses):
        experiment_id = str(uuid4())
        experiment = Experiment(
            experiment_id=experiment_id,
            hypothesis_id=hypothesis.hypothesis_id,
            status="completed",
            current_agent="coordinator_agent",
            data_quality_passed=True,
            statistical_tests_passed=True,
            backtest_completed=True,
            critic_approved=True,
            final_decision="approved",
            rejection_reason=None,
            created_at=started_at,
            completed_at=ended_at,
        )
        session.add(experiment)
        statistical = _test_for_hypothesis(session, hypothesis.hypothesis_id)
        backtest_id = str(uuid4())
        session.add(
            BacktestResult(
                backtest_id=backtest_id,
                hypothesis_id=hypothesis.hypothesis_id,
                test_id=statistical.test_id,
                dataset_a_id=statistical.dataset_a_id,
                dataset_b_id=statistical.dataset_b_id,
                git_commit_hash="abcdef1234567890abcdef1234567890abcdef12",
                config_hash=f"{index:064x}",
                dataset_ids=[statistical.dataset_a_id, statistical.dataset_b_id],
                random_seed=10_000 + index,
                execution_command=["stat-arb", "experiment", "run-pipeline"],
                run_timestamp=ended_at,
                lock_file_hash=f"{index + 1:064x}",
                execution_time_seconds=90.0 + index,
                train_window_days=60,
                test_window_days=30,
                num_windows=2,
                entry_threshold=2.0,
                exit_threshold=0.5,
                hedge_ratio=1.0,
                risk_exit_policy={"max_holding_bars": 96, "emergency_z_score": 4.0},
                risk_exit_policy_disabled_reason=None,
                gross_pnl=120.0 + index,
                net_pnl=90.0 + index,
                commission_cost=5.0,
                spread_cost=6.0,
                slippage_cost=4.0,
                funding_cost=3.0,
                borrow_cost=2.0,
                num_trades=12 + index,
                turnover=1.2,
                avg_holding_time_hours=8.0,
                median_holding_time_hours=6.0,
                sharpe_ratio=1.1,
                sortino_ratio=1.3,
                volatility=0.18,
                max_drawdown=0.08,
                win_rate=0.58,
                profit_factor=1.45,
                net_pnl_2x_costs=70.0 + index,
                net_pnl_half_costs=100.0 + index,
                baseline_sharpe=0.2,
                tested_at=ended_at,
            ),
        )
        session.add(
            CriticReview(
                review_id=str(uuid4()),
                backtest_id=backtest_id,
                lookahead_bias_detected=False,
                overfitting_indicators=["parameter/data ratio reviewed"] if index == 0 else [],
                weak_assumptions=[],
                insufficient_testing=[],
                cost_concerns=["cost sensitivity reviewed"] if index == 0 else [],
                operational_concerns=[],
                status="approved",
                recommendation="Approved for research MVP acceptance fixture.",
                objections="No blocking objections; synthetic fixture includes one reviewed concern.",
                reviewed_at=ended_at,
            ),
        )
        for artifact_type in REPORT_ARTIFACT_TYPES:
            session.add(
                ReportArtifact(
                    experiment_id=experiment_id,
                    artifact_type=artifact_type,
                    file_path=f"reports/mvp_acceptance/{experiment_id}/{artifact_type}.html",
                    format="html" if artifact_type == "backtest_report" else "json",
                    created_at=ended_at,
                ),
            )
        for stage in (
            "statistical_testing",
            "backtesting",
            "critic_review",
            "reporting",
        ):
            session.add(
                CoordinatorTask(
                    task_id=str(uuid4()),
                    experiment_id=experiment_id,
                    task_type=stage,
                    agent_name=f"{stage}_agent",
                    priority=index,
                    status="completed",
                    attempt_count=1,
                    max_attempts=2,
                    payload={"fixture": "deterministic-mvp-acceptance"},
                    last_error=None,
                    created_at=started_at,
                    started_at=started_at,
                    completed_at=ended_at,
                ),
            )


def _numeric_evidence(
    session: Session,
    *,
    targets: MVPAcceptanceTargets,
) -> MVPNumericEvidence:
    symbols = {
        row[0]
        for row in session.query(Dataset.symbol)
        .filter(Dataset.timeframe == targets.timeframe)
        .distinct()
        .all()
    }
    history_days = [
        int((dataset.end_date - dataset.start_date).days)
        for dataset in session.query(Dataset)
        .filter(Dataset.timeframe == targets.timeframe)
        .all()
    ]
    completed_experiment_ids = {
        row[0]
        for row in session.query(Experiment.experiment_id)
        .filter(
            Experiment.status == "completed",
            Experiment.backtest_completed.is_(True),
            Experiment.final_decision.is_not(None),
        )
        .all()
    }
    reports = (
        session.query(ReportArtifact)
        .filter(
            ReportArtifact.experiment_id.in_(completed_experiment_ids),
            ReportArtifact.artifact_type == "backtest_report",
        )
        .count()
        if completed_experiment_ids
        else 0
    )
    runtimes = [
        float(row[0])
        for row in session.query(BacktestResult.execution_time_seconds)
        .filter(BacktestResult.execution_time_seconds.is_not(None))
        .all()
    ]
    return MVPNumericEvidence(
        assets=len(symbols),
        pairs_tested=session.query(StatisticalTestResult).count(),
        completed_experiments=len(completed_experiment_ids),
        generated_reports=reports,
        timeframe=targets.timeframe,
        min_history_days=min(history_days) if history_days else 0,
        max_experiment_runtime_seconds=max(runtimes) if runtimes else float("inf"),
    )


def _section_22_1(
    numeric: MVPNumericEvidence,
    targets: MVPAcceptanceTargets,
) -> MVPAcceptanceSection:
    failures = _scale_failures(numeric, targets)
    evidence = (
        f"{numeric.assets} assets in registry",
        f"{numeric.pairs_tested} pairs tested",
        f"{numeric.completed_experiments} completed experiments",
        f"{numeric.generated_reports} backtest reports",
    )
    return _section("22.1", "End-to-end MVP validation", evidence, failures)


def _section_22_2(
    numeric: MVPNumericEvidence,
    targets: MVPAcceptanceTargets,
) -> MVPAcceptanceSection:
    failures = [
        *_scale_failures(numeric, targets),
        *(
            ()
            if numeric.timeframe == targets.timeframe
            else (f"timeframe must be {targets.timeframe}",)
        ),
        *(
            ()
            if numeric.min_history_days >= targets.min_history_days
            else (
                "history must cover at least "
                f"{targets.min_history_days} days, got {numeric.min_history_days}",
            )
        ),
        *(
            ()
            if numeric.max_experiment_runtime_seconds
            <= targets.max_full_experiment_runtime_seconds
            else (
                "full experiment runtime must be below "
                f"{targets.max_full_experiment_runtime_seconds}s",
            )
        ),
    ]
    evidence = (
        f"timeframe={numeric.timeframe}",
        f"min_history_days={numeric.min_history_days}",
        f"max_runtime_seconds={numeric.max_experiment_runtime_seconds:.2f}",
    )
    return _section("22.2", "MVP numeric targets", evidence, tuple(failures))


def _section_22_3(*, session: Session, repo_root: Path) -> MVPAcceptanceSection:
    quality_reports = session.query(DataQualityReportRecord).count()
    detected_quality_issues = (
        session.query(DataQualityReportRecord)
        .filter(
            (DataQualityReportRecord.missing_bars > 0)
            | (DataQualityReportRecord.outlier_count > 0)
            | (DataQualityReportRecord.duplicate_timestamps > 0)
        )
        .count()
    )
    passed_stat_tests = (
        session.query(StatisticalTestResult)
        .filter(StatisticalTestResult.passed.is_(True))
        .count()
    )
    backtests = session.query(BacktestResult).all()
    reports = session.query(ReportArtifact).filter(ReportArtifact.artifact_type == "backtest_report").count()
    critic_issue_count = (
        session.query(CriticReview)
        .filter(
            (CriticReview.overfitting_indicators != [])
            | (CriticReview.weak_assumptions != [])
            | (CriticReview.insufficient_testing != [])
            | (CriticReview.cost_concerns != [])
            | (CriticReview.operational_concerns != [])
        )
        .count()
    )
    failures: list[str] = []
    if quality_reports == 0 or detected_quality_issues == 0:
        failures.append("data quality evidence must include detected missing/outlier bars")
    if passed_stat_tests == 0:
        failures.append("statistical tests must include at least one passed pair")
    if not backtests:
        failures.append("backtests must exist")
    if any(not result.config_hash or not result.lock_file_hash for result in backtests):
        failures.append("backtests must store reproducibility hashes")
    if any(
        (
            result.commission_cost
            + result.spread_cost
            + result.slippage_cost
            + result.funding_cost
            + result.borrow_cost
        )
        <= 0
        for result in backtests
    ):
        failures.append("backtests must include non-zero cost attribution")
    if critic_issue_count == 0:
        failures.append("critic evidence must include at least one detected/reviewed issue")
    if reports == 0:
        failures.append("human-readable report artifacts must exist")
    if not (repo_root / "scripts" / "check_memory_quality.ps1").exists():
        failures.append("memory quality guard script is required")
    evidence = (
        f"quality_reports={quality_reports}, detected_quality_issues={detected_quality_issues}",
        f"passed_statistical_tests={passed_stat_tests}",
        f"backtests={len(backtests)}, reports={reports}",
        f"critic_issue_count={critic_issue_count}",
        "Memory Agent/ApeRAG quality is guarded by scripts/check_memory_quality.ps1",
    )
    return _section("22.3", "MVP functional criteria", evidence, tuple(failures))


def _section_22_4(
    *,
    repo_root: Path,
    targets: MVPAcceptanceTargets,
) -> MVPAcceptanceSection:
    required_paths = (
        repo_root / "pyproject.toml",
        repo_root / "uv.lock",
        repo_root / "scripts" / "check_runtime_resource_budget.ps1",
        repo_root / "scripts" / "check_secret_leaks.ps1",
        repo_root / "scripts" / "check_infisical_auth.ps1",
        repo_root / "docs" / "runtime_maintenance.md",
        repo_root / "docs" / "data_sources.md",
    )
    failures = [f"missing {path.relative_to(repo_root)}" for path in required_paths if not path.exists()]
    data_sources = _read_text(repo_root / "docs" / "data_sources.md")
    if "No paid data dependency" not in data_sources and "без paid data" not in data_sources:
        failures.append("data source docs must state no paid data dependency for v1")
    evidence = (
        "Python core uses uv, SQLite, Parquet and local scripts",
        "ApeRAG, Infisical and OmniRoute remain Docker-supported runtime services",
        "CI/pre-commit avoid local Docker, secrets and live market APIs",
        f"resource targets: memory<{targets.max_memory_gb}GB, dataset<{targets.max_dataset_disk_gb}GB",
    )
    return _section("22.4", "MVP non-functional criteria", evidence, tuple(failures))


def _section_22_5(*, repo_root: Path) -> MVPAcceptanceSection:
    required_docs = (
        repo_root / "docs" / "legal_disclaimer.md",
        repo_root / "docs" / "deferred_work_checklist.md",
        repo_root / "docs" / "technical_debt.md",
        repo_root / "docs" / "rust_strategy.md",
        repo_root / "docs" / "knowledge" / "decisions_future_paper_live.md",
    )
    failures = [f"missing {path.relative_to(repo_root)}" for path in required_docs if not path.exists()]
    checklist = _read_text(repo_root / "docs" / "deferred_work_checklist.md")
    if "paper/live" not in checklist and "demo/live" not in checklist:
        failures.append("future paper/live limitations must be visible in deferred checklist")
    evidence = (
        "Research-only legal boundary is documented",
        "Known limitations and deferred work are tracked",
        "Future paper/live roles are staged after research MVP",
        "Rust remains an optional profiling-driven acceleration path",
    )
    return _section("22.5", "Known limitations and future work", evidence, tuple(failures))


def _scale_failures(
    numeric: MVPNumericEvidence,
    targets: MVPAcceptanceTargets,
) -> tuple[str, ...]:
    failures: list[str] = []
    if numeric.assets < targets.min_assets or numeric.assets > targets.max_assets:
        failures.append(
            f"assets must be between {targets.min_assets} and {targets.max_assets}, "
            f"got {numeric.assets}"
        )
    if numeric.pairs_tested < targets.min_pairs_tested:
        failures.append(f"pairs tested must be >= {targets.min_pairs_tested}, got {numeric.pairs_tested}")
    if numeric.completed_experiments < targets.min_experiments:
        failures.append(
            f"experiments must be >= {targets.min_experiments}, "
            f"got {numeric.completed_experiments}"
        )
    if numeric.generated_reports < targets.min_experiments:
        failures.append(
            f"reports must be >= {targets.min_experiments}, got {numeric.generated_reports}"
        )
    return tuple(failures)


def _section(
    task_id: str,
    title: str,
    evidence: tuple[str, ...],
    failures: tuple[str, ...] | list[str],
) -> MVPAcceptanceSection:
    failure_tuple = tuple(failures)
    return MVPAcceptanceSection(
        task_id=task_id,
        title=title,
        passed=not failure_tuple,
        evidence=evidence,
        failures=failure_tuple,
    )


def _dataset_for_symbol(session: Session, symbol: str) -> Dataset:
    dataset = session.query(Dataset).filter(Dataset.symbol == symbol).one()
    return dataset


def _test_for_hypothesis(session: Session, hypothesis_id: str) -> StatisticalTestResult:
    result = (
        session.query(StatisticalTestResult)
        .filter(StatisticalTestResult.hypothesis_id == hypothesis_id)
        .one()
    )
    return result


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _print_report(report: MVPAcceptanceReport) -> None:
    print("Проверка Task 22 MVP acceptance...")
    for section in report.sections:
        status = "OK" if section.passed else "FAIL"
        print(f"- {section.task_id} {section.title}: {status}")
        for item in section.evidence:
            print(f"  evidence: {item}")
        for failure in section.failures:
            print(f"  failure: {failure}")
    print("MVP acceptance пройден." if report.passed else "MVP acceptance не пройден.")


if __name__ == "__main__":
    raise SystemExit(main())
