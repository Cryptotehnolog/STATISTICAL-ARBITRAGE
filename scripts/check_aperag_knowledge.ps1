param(
    [string]$EnvFile = "data\aperag\.env",
    [string]$CollectionTitle = "stat-arb-project-knowledge",
    [string]$Query = "What are the current memory backend decisions for the Statistical Arbitrage project?",
    [string[]]$Keywords = @(),
    [string[]]$ExpectedText = @(),
    [int]$TopK = 5
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot $EnvFile

if (-not (Test-Path -LiteralPath $envPath)) {
    Write-Error "ApeRAG env file не найден: $envPath"
}

Get-Content -LiteralPath $envPath | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)\s*$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}

$headers = @{
    Authorization = "Bearer $env:APERAG_API_KEY"
    "Content-Type" = "application/json"
}

function Invoke-ApeRagJson {
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null
    )

    $uri = "$env:APERAG_API_BASE_URL$Path"
    if ($null -eq $Body) {
        return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -TimeoutSec 60
    }

    $json = $Body | ConvertTo-Json -Depth 20
    return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -Body $json -TimeoutSec 60
}

function Get-SearchKeywords {
    param([string]$Text)

    $stopWords = @(
        "about", "after", "and", "are", "because", "before", "current", "for",
        "from", "how", "into", "project", "statistical", "the", "this", "what",
        "when", "where", "which", "why", "with"
    )
    $tokens = [regex]::Matches($Text.ToLowerInvariant(), "[a-z0-9][a-z0-9_-]{2,}") |
        ForEach-Object { $_.Value } |
        Where-Object { $stopWords -notcontains $_ } |
        Select-Object -Unique

    return @($tokens | Select-Object -First 8)
}

Write-Output "Проверка ApeRAG knowledge..."

$collections = Invoke-ApeRagJson -Method "GET" -Path "/api/v1/collections?page=1&page_size=100"
$collection = $collections.items | Where-Object { $_.title -eq $CollectionTitle } | Select-Object -First 1
if (-not $collection) {
    Write-Error "ApeRAG collection не найдена: $CollectionTitle"
}

$detail = Invoke-ApeRagJson -Method "GET" -Path "/api/v1/collections/$($collection.id)"
if (-not $detail.config.enable_vector -or -not $detail.config.enable_fulltext) {
    Write-Error "ApeRAG collection должна иметь enable_vector=true и enable_fulltext=true."
}

$docs = Invoke-ApeRagJson -Method "GET" -Path "/api/v1/collections/$($collection.id)/documents?page=1&page_size=100"
if (-not $docs.items -or $docs.items.Count -eq 0) {
    Write-Error "ApeRAG collection пуста."
}

$badDocs = @(
    $docs.items | Where-Object {
        $_.vector_index_status -ne "ACTIVE" -or
        $_.fulltext_index_status -ne "ACTIVE"
    }
)
if ($badDocs.Count -gt 0) {
    $badDocs | Select-Object name,status,vector_index_status,fulltext_index_status,graph_index_status | Format-Table -AutoSize
    Write-Error "ApeRAG documents имеют неготовые индексы: $($badDocs.Count)"
}

$resolvedKeywords = @($Keywords | Where-Object { $_ -and $_.Trim() } | ForEach-Object { $_.Trim() })
if ($resolvedKeywords.Count -eq 0) {
    $resolvedKeywords = @(Get-SearchKeywords -Text $Query)
}
if ($resolvedKeywords.Count -eq 0) {
    Write-Error "ApeRAG search keywords пусты. Передайте -Keywords или более содержательный -Query."
}

$search = Invoke-ApeRagJson -Method "POST" -Path "/api/v1/collections/$($collection.id)/searches" -Body @{
    query = $Query
    vector_search = @{
        topk = $TopK
        similarity = 0.1
    }
    fulltext_search = @{
        topk = $TopK
        keywords = $resolvedKeywords
    }
    save_to_history = $false
    rerank = $false
}

if (-not $search.items -or $search.items.Count -eq 0) {
    Write-Error "ApeRAG smoke search не вернул results."
}

$combinedText = (($search.items | ForEach-Object {
    $titles = ""
    if ($_.metadata -and $_.metadata.titles) {
        $titles = ($_.metadata.titles -join " ")
    }
    "$($_.content) $($_.text) $($_.source) $($_.metadata.title) $titles"
}) -join "`n")
$normalizedCombinedText = ($combinedText -replace "\s+", " ").Trim()
$missingExpected = @(
    $ExpectedText | Where-Object {
        $_ -and $normalizedCombinedText -notmatch [regex]::Escape(($_ -replace "\s+", " ").Trim())
    }
)
if ($missingExpected.Count -gt 0) {
    Write-Error "ApeRAG search results не содержат expected text: $($missingExpected -join ', ')"
}

Write-Output "ApeRAG knowledge OK: docs=$($docs.items.Count), search_results=$($search.items.Count), keywords=$($resolvedKeywords -join ', ')"
