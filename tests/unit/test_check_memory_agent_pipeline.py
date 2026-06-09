"""Static tests for the Memory Agent pipeline check command."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_memory_agent_pipeline.ps1")


def test_check_memory_agent_pipeline_runs_contract_tests_and_guards() -> None:
    """Memory Agent checkpoint should cover deterministic tests and boundary guards."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "test_memory_agent_full.py" in script
    assert "test_memory_policy.py" in script
    assert "check_memory_contracts.ps1" in script
    assert "check_no_legacy_memory_backend_imports.ps1" in script
    assert ".venv\\Scripts\\python.exe" in script
    assert ".venv/bin/python" in script
    assert "tests/unit/test_memory_agent_full.py" in script
    assert "tests\\unit\\test_memory_agent_full.py" not in script
    assert "Invoke-RequiredCheck $memoryContractsCheckScript" in script
    assert "Invoke-RequiredCheck $legacyMemoryImportsCheckScript" in script
    assert "--no-cov" in script
    assert "-p no:cacheprovider" in script


def test_check_memory_agent_pipeline_keeps_runtime_health_optional() -> None:
    """Ordinary Memory Agent checks should not depend on external ApeRAG runtime."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "$IncludeRuntimeHealth" in script
    assert "используйте -IncludeRuntimeHealth" in script
