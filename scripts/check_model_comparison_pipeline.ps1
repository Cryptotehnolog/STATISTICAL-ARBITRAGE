param(
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

if (-not $Quiet) {
    Write-Output "Проверка model-comparison pipeline..."
}

uv run pytest tests/unit/test_model_comparison.py tests/unit/test_check_model_comparison_pipeline.py -q

if (-not $Quiet) {
    Write-Output "Model comparison pipeline OK"
}
