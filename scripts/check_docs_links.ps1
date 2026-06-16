param(
    [string[]]$Paths = @(
        "README.md",
        "docs",
        ".kiro\specs"
    )
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

$excludedPathParts = @(
    ".venv",
    ".uv-cache",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "data",
    "docs\knowledge_graph",
    "htmlcov"
)

function Test-IsExcluded {
    param([string]$RelativePath)

    $normalized = $RelativePath -replace "/", "\"
    foreach ($part in $excludedPathParts) {
        if ($normalized.StartsWith($part, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

function Get-MarkdownFiles {
    foreach ($path in $Paths) {
        $resolved = Join-Path $repoRoot $path
        if (-not (Test-Path -LiteralPath $resolved)) {
            continue
        }

        $item = Get-Item -LiteralPath $resolved
        if ($item.PSIsContainer) {
            Get-ChildItem -LiteralPath $resolved -Recurse -File -Filter "*.md"
        }
        else {
            $item
        }
    }
}

function Test-IsExternalLink {
    param([string]$Target)

    return $Target -match "^[a-zA-Z][a-zA-Z0-9+.-]*:" -or
        $Target.StartsWith("#") -or
        $Target.StartsWith("mailto:") -or
        $Target.StartsWith("tel:")
}

function Test-LooksLikeLocalMarkdownPath {
    param([string]$Target)

    $withoutAnchor = ($Target -split "#", 2)[0]
    return $withoutAnchor -match '(^|[\\/])[^\\/]+\.md$'
}

function Test-LooksLikeRepoRootMarkdownPath {
    param([string]$Target)

    $withoutAnchor = ($Target -split "#", 2)[0]
    return $withoutAnchor -match '^(README\.md|docs[\\/].+\.md|\.kiro[\\/].+\.md)$'
}

function Resolve-LocalTargetPath {
    param(
        [System.IO.FileInfo]$SourceFile,
        [string]$Target
    )

    $withoutAnchor = ($Target -split "#", 2)[0]
    if ([string]::IsNullOrWhiteSpace($withoutAnchor)) {
        return $null
    }

    $decoded = [System.Uri]::UnescapeDataString($withoutAnchor)
    if ([System.IO.Path]::IsPathRooted($decoded)) {
        return $decoded
    }

    $baseDir = Split-Path -Parent $SourceFile.FullName
    return [System.IO.Path]::GetFullPath((Join-Path $baseDir $decoded))
}

function Test-WildcardTargetExists {
    param(
        [System.IO.FileInfo]$SourceFile,
        [string]$Target
    )

    $withoutAnchor = ($Target -split "#", 2)[0]
    if (-not $withoutAnchor.Contains("*")) {
        return $false
    }

    $baseDir = Split-Path -Parent $SourceFile.FullName
    $pattern = Join-Path $baseDir $withoutAnchor
    $matches = Get-ChildItem -Path $pattern -File -ErrorAction SilentlyContinue
    return $null -ne ($matches | Select-Object -First 1)
}

function Test-IsSupportedStatArbCommand {
    param([string]$Line)

    $supportedStatArbCommands = @(
        "data download",
        "data list",
        "data validate",
        "experiment advance",
        "experiment execute-stage",
        "experiment list",
        "experiment run-pipeline",
        "experiment run-stage",
        "experiment status",
        "hypothesis add",
        "hypothesis generate",
        "hypothesis list"
    )

    $match = [regex]::Match(
        $Line,
        '\buv\s+run\s+stat-arb\s+([A-Za-z0-9_-]+)(?:\s+([A-Za-z0-9_-]+))?'
    )
    if (-not $match.Success) {
        return $false
    }

    $command = $match.Groups[1].Value
    if ($match.Groups[2].Success) {
        $command = "$command $($match.Groups[2].Value)"
    }

    return $supportedStatArbCommands -contains $command
}

$violations = @()
$linkPattern = '(?<!\!)\[[^\]]+\]\(([^)]+)\)'
$inlineMarkdownPathPattern = '`([^`]+\.md(?:#[^`]*)?)`'
$scriptCommandPattern = '(?:\.\\|\.\/)scripts[\\/][A-Za-z0-9_.-]+\.ps1'
$statArbCommandPattern = '\buv\s+run\s+stat-arb\b'
$pyprojectPath = Join-Path $repoRoot "pyproject.toml"
$pyprojectText = if (Test-Path -LiteralPath $pyprojectPath) {
    Get-Content -LiteralPath $pyprojectPath -Raw
}
else {
    ""
}

foreach ($file in Get-MarkdownFiles | Sort-Object FullName -Unique) {
    $relative = $file.FullName.Substring($repoRoot.Length + 1)
    if (Test-IsExcluded -RelativePath $relative) {
        continue
    }

    $lines = Get-Content -LiteralPath $file.FullName
    for ($index = 0; $index -lt $lines.Count; $index++) {
        foreach ($match in [regex]::Matches($lines[$index], $linkPattern)) {
            $target = $match.Groups[1].Value.Trim()
            if ($target.StartsWith("<") -and $target.EndsWith(">")) {
                $target = $target.Substring(1, $target.Length - 2)
            }
            if (Test-IsExternalLink -Target $target) {
                continue
            }
            if (-not (Test-LooksLikeRepoRootMarkdownPath -Target $target)) {
                continue
            }

            $repoRootFile = Get-Item -LiteralPath (Join-Path $repoRoot "README.md")
            if ($target.Contains("*")) {
                if (Test-WildcardTargetExists -SourceFile $repoRootFile -Target $target) {
                    continue
                }
                else {
                    $violations += [pscustomobject]@{
                        File = $relative
                        Line = $index + 1
                        Target = $target
                        Kind = "unmatched wildcard local markdown paths"
                    }
                    continue
                }
            }

            $targetPath = Resolve-LocalTargetPath -SourceFile $repoRootFile -Target $target
            if ($null -eq $targetPath) {
                continue
            }

            $repoRootFull = [System.IO.Path]::GetFullPath($repoRoot)
            if (-not $targetPath.StartsWith($repoRootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
                continue
            }

            if (-not (Test-Path -LiteralPath $targetPath)) {
                $violations += [pscustomobject]@{
                    File = $relative
                    Line = $index + 1
                    Target = $target
                }
            }
        }

        foreach ($match in [regex]::Matches($lines[$index], $inlineMarkdownPathPattern)) {
            $target = $match.Groups[1].Value.Trim()
            if (Test-IsExternalLink -Target $target) {
                continue
            }
            if (-not (Test-LooksLikeRepoRootMarkdownPath -Target $target)) {
                continue
            }

            $repoRootFile = Get-Item -LiteralPath (Join-Path $repoRoot "README.md")
            if ($target.Contains("*")) {
                if (Test-WildcardTargetExists -SourceFile $repoRootFile -Target $target) {
                    continue
                }
                else {
                    $violations += [pscustomobject]@{
                        File = $relative
                        Line = $index + 1
                        Target = $target
                        Kind = "unmatched wildcard local markdown paths"
                    }
                    continue
                }
            }

            $targetPath = Resolve-LocalTargetPath -SourceFile $repoRootFile -Target $target
            if ($null -eq $targetPath) {
                continue
            }

            $repoRootFull = [System.IO.Path]::GetFullPath($repoRoot)
            if (-not $targetPath.StartsWith($repoRootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
                continue
            }

            if (-not (Test-Path -LiteralPath $targetPath)) {
                $violations += [pscustomobject]@{
                    File = $relative
                    Line = $index + 1
                    Target = $target
                    Kind = "inline code local markdown paths"
                }
            }
        }

        foreach ($match in [regex]::Matches($lines[$index], $scriptCommandPattern)) {
            $target = $match.Value.Trim()
            $normalizedTarget = $target.Substring(2) -replace "/", "\"
            $targetPath = Join-Path $repoRoot $normalizedTarget
            if (-not (Test-Path -LiteralPath $targetPath)) {
                $violations += [pscustomobject]@{
                    File = $relative
                    Line = $index + 1
                    Target = $target
                    Kind = "referenced script commands"
                }
            }
        }

        if ($lines[$index] -match $statArbCommandPattern) {
            if ($pyprojectText -notmatch '(?m)^\s*stat-arb\s*=') {
                $violations += [pscustomobject]@{
                    File = $relative
                    Line = $index + 1
                    Target = "uv run stat-arb"
                    Kind = "referenced stat-arb commands"
                }
            }
            elseif (-not (Test-IsSupportedStatArbCommand -Line $lines[$index])) {
                $violations += [pscustomobject]@{
                    File = $relative
                    Line = $index + 1
                    Target = $lines[$index].Trim()
                    Kind = "unsupported stat-arb commands"
                }
            }
        }
    }
}

if ($violations.Count -gt 0) {
    Write-Output "Найдены битые local markdown links:"
    $violations | Format-Table -AutoSize
    Write-Error "Проверка local markdown links не прошла."
}

Write-Output "Проверка local markdown links прошла."
