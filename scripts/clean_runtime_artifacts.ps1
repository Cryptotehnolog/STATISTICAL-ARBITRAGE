param(
    [switch]$Apply,
    [switch]$IncludeSmokeArtifacts
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Add-ExistingPath {
    param(
        [System.Collections.ArrayList]$Paths,
        [string]$Path
    )

    $fullPath = Join-Path $repoRoot $Path
    if (Test-Path -LiteralPath $fullPath) {
        [void]$Paths.Add((Resolve-Path -LiteralPath $fullPath).Path)
    }
}

function Add-ExistingDirectoriesByName {
    param(
        [System.Collections.ArrayList]$Paths,
        [string[]]$Roots,
        [string]$Name
    )

    foreach ($root in $Roots) {
        $fullRoot = Join-Path $repoRoot $root
        if (-not (Test-Path -LiteralPath $fullRoot)) {
            continue
        }

        Get-ChildItem -LiteralPath $fullRoot -Recurse -Force -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -eq $Name } |
            ForEach-Object { [void]$Paths.Add($_.FullName) }
    }
}

$targets = [System.Collections.ArrayList]::new()

Add-ExistingPath -Paths $targets -Path ".ruff_cache"
Add-ExistingPath -Paths $targets -Path ".pytest_cache"
Add-ExistingPath -Paths $targets -Path "coverage.xml"
Add-ExistingPath -Paths $targets -Path "htmlcov"
Add-ExistingPath -Paths $targets -Path "data/test_tmp"
Add-ExistingPath -Paths $targets -Path "data/test_registry.db"

Get-ChildItem -LiteralPath $repoRoot -Force -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like ".coverage*" } |
    ForEach-Object { [void]$targets.Add($_.FullName) }

Get-ChildItem -LiteralPath (Join-Path $repoRoot "data") -Force -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "memory_graph_viewer_server*.json" } |
    Where-Object {
        try {
            $state = Get-Content -Raw -LiteralPath $_.FullName | ConvertFrom-Json
            if ($state.pid -and (Get-Process -Id $state.pid -ErrorAction SilentlyContinue)) {
                return $false
            }
        }
        catch {
            return $true
        }
        return $true
    } |
    ForEach-Object { [void]$targets.Add($_.FullName) }

Add-ExistingDirectoriesByName `
    -Paths $targets `
    -Roots @("src", "tests") `
    -Name "__pycache__"

if ($IncludeSmokeArtifacts) {
}

$uniqueTargets = @($targets | Sort-Object -Unique)
if ($uniqueTargets.Count -eq 0) {
    Write-Output "Runtime/cache artifacts для удаления не найдены."
    exit 0
}

if (-not $Apply) {
    Write-Output "Dry-run: будут удалены следующие regenerable artifacts:"
    $uniqueTargets | ForEach-Object { Write-Output "- $_" }
    Write-Output "Для удаления запустите: .\scripts\clean_runtime_artifacts.ps1 -Apply"
    Write-Output "Для smoke/benchmark artifacts добавьте: -IncludeSmokeArtifacts"
    exit 0
}

foreach ($target in $uniqueTargets) {
    $resolved = Resolve-Path -LiteralPath $target -ErrorAction SilentlyContinue
    if (-not $resolved) {
        continue
    }

    $path = $resolved.Path
    if (-not $path.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        Write-Error "Отказ удалять путь вне repository: $path"
    }

    Remove-Item -LiteralPath $path -Recurse -Force
    Write-Output "Удалено: $path"
}

Write-Output "Чистка runtime/cache artifacts завершена."
