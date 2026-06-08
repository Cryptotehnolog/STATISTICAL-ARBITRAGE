"""Static tests for FreeDeepseekAPI model benchmark automation."""

from pathlib import Path

SCRIPT = Path("scripts/benchmark_free_deepseek_models.ps1")


def test_benchmark_free_deepseek_models_covers_aliases_and_writes_json() -> None:
    """Benchmark should compare known aliases and persist local measurements."""
    script = SCRIPT.read_text(encoding="utf-8")

    assert "deepseek-chat" in script
    assert "deepseek-v3" in script
    assert "deepseek-default" in script
    assert "deepseek-reasoner" in script
    assert "deepseek-r1" in script
    assert "deepseek-expert" in script
    assert "deepseek-v4-pro" in script
    assert "data\\free_deepseek\\model_benchmark.json" in script
    assert "ConvertTo-Json" in script


def test_benchmark_free_deepseek_models_keeps_parallel_probe_explicit() -> None:
    """Parallel probing should be opt-in to avoid hammering DeepSeek Web."""
    script = SCRIPT.read_text(encoding="utf-8")

    assert "[switch]$IncludeParallelProbe" in script
    assert "Start-Job" in script
    assert "parallel_chat_limit" in script
    assert "Сообщение генерируется" in script
    assert "Параллельная проверка отключена" in script


def test_benchmark_free_deepseek_models_does_not_mix_logs_into_results() -> None:
    """Progress logs must not be emitted through the object pipeline."""
    script = SCRIPT.read_text(encoding="utf-8")

    assert 'Write-Host "Model: $model"' in script
    assert 'Write-Output "Model: $model"' not in script
