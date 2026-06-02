$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$checkScript = Join-Path $PSScriptRoot "check.ps1"
$russianCheckScript = Join-Path $PSScriptRoot "check_user_facing_russian.ps1"

Write-Output "Запуск локального pre-commit checklist..."
Write-Output "- Русификация user-facing текста: check_user_facing_russian.ps1"
Write-Output "- Unit и lint baseline: check.ps1"
Write-Output "- LLM readiness намеренно исключен; отдельно запускайте check_omniroute.ps1."

Push-Location $repoRoot
try {
    & $russianCheckScript
    & $checkScript
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
