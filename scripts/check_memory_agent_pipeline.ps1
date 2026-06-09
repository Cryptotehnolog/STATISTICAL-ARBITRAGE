param(
    [switch]$IncludeRuntimeHealth
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$windowsPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$linuxPython = Join-Path $repoRoot ".venv/bin/python"
$python = if (Test-Path -LiteralPath $windowsPython) { $windowsPython } else { $linuxPython }
$memoryContractsCheckScript = Join-Path $PSScriptRoot "check_memory_contracts.ps1"
$legacyMemoryImportsCheckScript = Join-Path $PSScriptRoot "check_no_legacy_memory_backend_imports.ps1"
$memoryHealthCheckScript = Join-Path $PSScriptRoot "check_memory_health.ps1"
$env:PYTHONDONTWRITEBYTECODE = "1"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Ожидался Python из virtualenv: $windowsPython или $linuxPython. Сначала выполните 'uv sync'."
}

function Invoke-RequiredCheck {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath
    )

    $global:LASTEXITCODE = 0
    & $ScriptPath
    if ($LASTEXITCODE -ne 0) {
        throw "Проверка завершилась с ошибкой: $ScriptPath (exit code $LASTEXITCODE)"
    }
}

Write-Output "Проверка Memory Agent pipeline..."

Push-Location $repoRoot
try {
    Write-Output "- Unit/integration contracts"
    & $python -m pytest `
        tests/unit/test_memory_agent_full.py `
        tests/unit/test_memory_policy.py `
        tests/unit/test_memory_data_quality.py `
        tests/unit/test_aperag_client.py `
        tests/integration/test_memory_agent_service_integration.py `
        -q `
        --no-cov `
        -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    Write-Output "- Boundary guards"
    Invoke-RequiredCheck $memoryContractsCheckScript
    Invoke-RequiredCheck $legacyMemoryImportsCheckScript

    if ($IncludeRuntimeHealth) {
        Write-Output "- ApeRAG runtime health"
        Invoke-RequiredCheck $memoryHealthCheckScript
    }
    else {
        Write-Output "- ApeRAG runtime health пропущена (используйте -IncludeRuntimeHealth)"
    }
}
finally {
    Pop-Location
}

Write-Output "Memory Agent pipeline OK."
