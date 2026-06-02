param(
    [switch]$SkipGuard,
    [switch]$SkipDocker,
    [switch]$SkipQuery,
    [switch]$SkipViewerExport
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$dataDir = Join-Path $repoRoot "data"
$backupRoot = Join-Path $dataDir "backups"
$lightragDir = Join-Path $dataDir "lightrag"
$manifestPath = Join-Path $dataDir "lightrag_seed_manifest.json"
$seedScript = Join-Path $PSScriptRoot "seed_lightrag_curated.ps1"
$guardScript = Join-Path $PSScriptRoot "check_lightrag_memory_fresh.ps1"

function Move-ToBackup {
    param(
        [string]$Path,
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $target = Join-Path $backupRoot "$Name`_$stamp"
    Move-Item -LiteralPath $Path -Destination $target
    Write-Output "Backup создан: $target"
}

Write-Output "Чистая пересборка LightRAG из curated docs/knowledge/*.md..."

Move-ToBackup -Path $lightragDir -Name "lightrag"
Move-ToBackup -Path $manifestPath -Name "lightrag_seed_manifest.json"

Write-Output "- Seed curated memory"
& $seedScript -Apply -Force
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not $SkipGuard) {
    Write-Output "- Проверка rebuilt memory"
    $guardArgs = @()
    if ($SkipDocker) {
        $guardArgs += "-SkipDocker"
    }
    if ($SkipQuery) {
        $guardArgs += "-SkipQuery"
    }
    if ($SkipViewerExport) {
        $guardArgs += "-SkipViewerExport"
    }
    & $guardScript @guardArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
else {
    Write-Output "- Guard пропущен по флагу -SkipGuard"
}

Write-Output "Чистая пересборка LightRAG завершена."
