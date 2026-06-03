$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$checkScript = Join-Path $PSScriptRoot "check.ps1"
$russianCheckScript = Join-Path $PSScriptRoot "check_user_facing_russian.ps1"
$secretLeakCheckScript = Join-Path $PSScriptRoot "check_secret_leaks.ps1"
$memoryContractsCheckScript = Join-Path $PSScriptRoot "check_memory_contracts.ps1"
$legacyLightRagSurfaceCheckScript = Join-Path $PSScriptRoot "check_no_legacy_lightrag_user_surface.ps1"
$legacyLightRagImportsCheckScript = Join-Path $PSScriptRoot "check_no_legacy_lightrag_imports.ps1"

Write-Output "Запуск локального pre-commit checklist..."
Write-Output "- Русификация user-facing текста: check_user_facing_russian.ps1"
Write-Output "- Secret leak guard: check_secret_leaks.ps1"
Write-Output "- Проверка memory contracts: check_memory_contracts.ps1"
Write-Output "- Проверка активной пользовательской memory surface: check_no_legacy_lightrag_user_surface.ps1"
Write-Output "- Проверка отсутствия legacy LightRAG imports: check_no_legacy_lightrag_imports.ps1"
Write-Output "- Unit и lint baseline: check.ps1"
Write-Output "- LLM readiness намеренно исключен; отдельно запускайте check_omniroute.ps1."

Push-Location $repoRoot
try {
    & $russianCheckScript
    & $secretLeakCheckScript
    & $memoryContractsCheckScript
    & $legacyLightRagSurfaceCheckScript
    & $legacyLightRagImportsCheckScript
    & $checkScript
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
