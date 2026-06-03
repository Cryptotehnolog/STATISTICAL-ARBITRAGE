"""Unit tests for the task 5 data pipeline checkpoint."""

from pathlib import Path

from stat_arb.scripts.check_data_pipeline import run_checkpoint

WRAPPER_PATH = Path("scripts/check_data_pipeline.ps1")


def test_data_pipeline_checkpoint_runs_full_boundary() -> None:
    """Checkpoint should verify parquet, registry, sidecars, and memory boundary."""
    result = run_checkpoint()

    assert result.dataset_rows == 1
    assert result.quality_report_rows == 1
    assert result.parquet_rows == 3
    assert result.memory_filename.startswith("data-quality-failure-data-quality-report-")
    assert result.memory_document_ids == ("checkpoint-memory-doc",)


def test_check_data_pipeline_wrapper_uses_local_venv() -> None:
    """PowerShell wrapper should run the deterministic Python checkpoint."""
    script = WRAPPER_PATH.read_text(encoding="utf-8")

    assert ".venv\\Scripts\\python.exe" in script
    assert "stat_arb.scripts.check_data_pipeline" in script
    assert "Проверка data pipeline checkpoint" in script
