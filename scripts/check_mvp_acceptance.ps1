$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$outputPath = Join-Path $repoRoot "data\mvp_acceptance\mvp_acceptance_report.json"

Push-Location $repoRoot
try {
    Write-Output "Проверка Task 22 MVP acceptance..."
    uv run python -m stat_arb.scripts.check_mvp_acceptance `
        --repo-root $repoRoot `
        --output-json $outputPath
    if ($LASTEXITCODE -ne 0) {
        throw "Task 22 MVP acceptance не пройден."
    }
    Write-Output "Отчет MVP acceptance: $outputPath"
}
finally {
    Pop-Location
}
