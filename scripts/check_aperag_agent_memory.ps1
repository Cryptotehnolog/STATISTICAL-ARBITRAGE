param(
    [string]$EnvFile = "data\aperag\.env",
    [string]$CollectionTitle = "stat-arb-agent-memory",
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$windowsPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$linuxPython = Join-Path $repoRoot ".venv/bin/python"
$python = if (Test-Path -LiteralPath $windowsPython) { $windowsPython } else { $linuxPython }

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Ожидался Python из virtualenv: $windowsPython или $linuxPython. Сначала выполните 'uv sync'."
}

Write-Output "Проверка ApeRAG operational agent memory..."

Push-Location $repoRoot
try {
    .\scripts\configure_aperag.ps1 -EnvFile $EnvFile | Write-Output
    & $python -m stat_arb.scripts.smoke_aperag_agent_memory `
        --env-file $EnvFile `
        --collection-title $CollectionTitle `
        --timeout-seconds $TimeoutSeconds
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
