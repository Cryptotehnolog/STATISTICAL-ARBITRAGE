param(
    [string[]]$Paths = @(
        ".kiro\specs",
        "README.md",
        "docs"
    ),
    [int]$MinFileChars = 12000,
    [int]$MinSectionChars = 4000,
    [int]$TopSections = 8
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Get-MarkdownFiles {
    param([string[]]$InputPaths)

    foreach ($inputPath in $InputPaths) {
        $resolved = Join-Path $repoRoot $inputPath
        if (-not (Test-Path -LiteralPath $resolved)) {
            continue
        }

        $item = Get-Item -LiteralPath $resolved
        if ($item.PSIsContainer) {
            Get-ChildItem -LiteralPath $resolved -Recurse -Filter "*.md" -File
        }
        elseif ($item.Extension -eq ".md") {
            $item
        }
    }
}

function Get-MarkdownSections {
    param(
        [System.IO.FileInfo]$File,
        [int]$MinimumChars
    )

    $lines = Get-Content -LiteralPath $File.FullName
    $headings = @()
    $inFence = $false
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match '^\s*```') {
            $inFence = -not $inFence
            continue
        }
        if ($inFence) {
            continue
        }
        if ($lines[$index] -match '^(#{1,3})\s+(.+)$') {
            if ($Matches[1].Length -eq 1) {
                continue
            }
            $headings += [pscustomobject]@{
                Line = $index + 1
                Level = $Matches[1].Length
                Title = $Matches[2].Trim()
            }
        }
    }

    for ($index = 0; $index -lt $headings.Count; $index++) {
        $heading = $headings[$index]
        $next = $null
        for ($nextIndex = $index + 1; $nextIndex -lt $headings.Count; $nextIndex++) {
            if ($headings[$nextIndex].Level -le $heading.Level) {
                $next = $headings[$nextIndex]
                break
            }
        }

        $startLine = $heading.Line
        $endLine = if ($next) { $next.Line - 1 } else { $lines.Count }
        $text = ($lines[($startLine - 1)..($endLine - 1)] -join "`n")
        if ($text.Length -ge $MinimumChars) {
            [pscustomobject]@{
                File = $File.FullName.Substring($repoRoot.Length + 1)
                Line = $startLine
                Heading = ("#" * $heading.Level) + " " + $heading.Title
                Chars = $text.Length
            }
        }
    }
}

$files = @(Get-MarkdownFiles -InputPaths $Paths | Sort-Object FullName -Unique)
$largeFiles = @(
    $files |
        ForEach-Object {
            $content = Get-Content -LiteralPath $_.FullName -Raw
            [pscustomobject]@{
                File = $_.FullName.Substring($repoRoot.Length + 1)
                Chars = $content.Length
            }
        } |
        Where-Object { $_.Chars -ge $MinFileChars } |
        Sort-Object Chars -Descending
)

Write-Output "Большие markdown files (>= $MinFileChars chars):"
if ($largeFiles.Count -eq 0) {
    Write-Output "  Нет"
}
else {
    $largeFiles | Format-Table -AutoSize
}

$sections = @(
    foreach ($file in $files) {
        Get-MarkdownSections -File $file -MinimumChars $MinSectionChars
    }
)

Write-Output ""
Write-Output "Секции-кандидаты для docs/knowledge shards (>= $MinSectionChars chars):"
if ($sections.Count -eq 0) {
    Write-Output "  Нет"
}
else {
    $sections |
        Sort-Object Chars -Descending |
        Select-Object -First $TopSections |
        Format-Table -AutoSize
}

Write-Output ""
Write-Output "Рекомендуемое действие:"
Write-Output "- Не редактировать .kiro source specs ради cleanup памяти."
Write-Output "- Создавать краткие shards в docs/knowledge/ со ссылками на источники."
Write-Output "- Предпочитать decisions, contracts, workflows и safety rules вместо raw copied sections."
