"""Unit tests for data-quality failure memory helpers."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from stat_arb.domain import (
    DataQualityIssue,
    DataQualityReport,
    DataQualitySeverity,
    DatasetSource,
)
from stat_arb.memory import (
    MemoryAgentService,
    MemoryRecordType,
    data_quality_failure_memory_request,
    write_data_quality_failure_memory,
)


class FakeApeRAGClient:
    """Fake ApeRAG client for policy-approved memory writes."""

    def __init__(self) -> None:
        self.config = type("Config", (), {"agent_collection_title": "stat-arb-agent-memory"})()
        self.calls: list[dict[str, str]] = []

    def write_markdown_document(
        self,
        *,
        filename: str,
        content: str,
        collection_title: str | None = None,
        collection_id: str | None = None,
    ) -> list[str]:
        self.calls.append(
            {
                "filename": filename,
                "content": content,
                "collection_title": collection_title or "",
                "collection_id": collection_id or "",
            }
        )
        return ["dq-memory-doc-1"]


def _failed_report() -> DataQualityReport:
    start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    end = datetime(2024, 1, 1, 0, 10, tzinfo=UTC)
    return DataQualityReport(
        dataset_id=uuid4(),
        symbol="BTC/USDT",
        source=DatasetSource.CCXT,
        timeframe="5m",
        start_date=start,
        end_date=end,
        bar_count=2,
        expected_bar_count=3,
        missing_bars=1,
        timezone_normalized=True,
        alignment_score=0.667,
        quality_score=0.667,
        passed=False,
        issues=[
            DataQualityIssue(
                code="missing_bars",
                severity=DataQualitySeverity.ERROR,
                message="Missing OHLCV bars detected.",
                count=1,
                first_timestamp=end,
                last_timestamp=end,
            )
        ],
    )


def test_data_quality_failure_memory_request_is_policy_safe() -> None:
    """Failed reports should become concise Memory Agent write requests."""
    report = _failed_report()

    request = data_quality_failure_memory_request(report)

    assert request.record_type == MemoryRecordType.DATA_QUALITY_FAILURE
    assert request.title == "Data quality failure: BTC/USDT 5m"
    assert request.source_id == f"data-quality-report-{report.report_id}"
    assert request.registry_reference == f"registry:data_quality_reports/{report.report_id}"
    assert request.tags == ["5m", "btc/usdt", "data-quality", "failure"]
    assert request.metadata["dataset_id"] == str(report.dataset_id)


def test_write_data_quality_failure_memory_uses_policy_service() -> None:
    """Data-quality failure memory writes should go through MemoryAgentService."""
    client = FakeApeRAGClient()
    service = MemoryAgentService(client)  # type: ignore[arg-type]

    result = write_data_quality_failure_memory(service, _failed_report())

    assert result.document_ids == ("dq-memory-doc-1",)
    assert result.filename.startswith("data-quality-failure-data-quality-report-")
    assert client.calls[0]["collection_title"] == "stat-arb-agent-memory"
    assert "Record type: data_quality_failure" in client.calls[0]["content"]


def test_data_quality_failure_memory_request_rejects_passed_reports() -> None:
    """Passed reports should not create failure memory records."""
    report = _failed_report().model_copy(update={"passed": True, "issues": []})

    with pytest.raises(ValueError, match="Only failed data quality reports"):
        data_quality_failure_memory_request(report)
