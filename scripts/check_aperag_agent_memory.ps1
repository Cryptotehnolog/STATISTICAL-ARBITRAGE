param(
    [string]$EnvFile = "data\aperag\.env",
    [string]$CollectionTitle = "stat-arb-agent-memory",
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Ожидался Python из virtualenv: $python. Сначала выполните 'uv sync'."
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
        Write-Error "Проверка ApeRAG operational agent memory не прошла."
    }
}
finally {
    Pop-Location
}
