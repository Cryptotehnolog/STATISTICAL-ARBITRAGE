param(
    [string]$EnvFile = "data\aperag\.env",
    [string]$CollectionTitle = "stat-arb-project-knowledge",
    [ValidateSet("omniroute", "free_deepseek", "free_qwen")]
    [string]$CompletionBackend = "omniroute",
    [string]$CompletionProvider = "",
    [string]$CompletionModel = "",
    [int]$TimeoutSeconds = 900,
    [int]$MaxRetries = 2,
    [int]$RetryDelaySeconds = 30,
    [int]$GraphPollSeconds = 10,
    [switch]$FullRebuild
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
$sequentialGraphRebuild = $CompletionBackend -eq "free_deepseek"
if ($sequentialGraphRebuild) {
    if (-not $PSBoundParameters.ContainsKey("MaxRetries")) {
        $MaxRetries = 5
    }
    if (-not $PSBoundParameters.ContainsKey("RetryDelaySeconds")) {
        $RetryDelaySeconds = 60
    }
}

function Invoke-ApeRagJson {
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null,
        [int]$TimeoutSec = 60
    )

    $uri = "$env:APERAG_API_BASE_URL$Path"
    if ($null -eq $Body) {
        return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -TimeoutSec $TimeoutSec
    }

    $json = $Body | ConvertTo-Json -Depth 30
    return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -Body $json -TimeoutSec $TimeoutSec
}

function ConvertTo-PlainObject {
    param([object]$Value)

    if ($null -eq $Value) {
        return $null
    }
    if ($Value -is [System.Array]) {
        return @($Value | ForEach-Object { ConvertTo-PlainObject $_ })
    }
    if ($Value -is [System.Management.Automation.PSCustomObject]) {
        $hash = @{}
        foreach ($property in $Value.PSObject.Properties) {
            $hash[$property.Name] = ConvertTo-PlainObject $property.Value
        }
        return $hash
    }
    return $Value
}

function Test-TransientGraphFailure {
    param(
        [object[]]$FailedDocuments,
        [datetime]$GraphRebuildStartedAt
    )

    $knownTransientPatterns = @(
        "ALL_ACCOUNTS_INACTIVE",
        "all upstream accounts are inactive",
        "ServiceUnavailable",
        "service_unavailable",
        "temporarily unavailable",
        "rate limit",
        "Too Many Requests",
        "parallel_chat_limit",
        "Сообщение генерируется"
    )

    $logs = ""
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        try {
            Start-Sleep -Seconds 5
            $since = $GraphRebuildStartedAt.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
            $logs = (docker logs aperag-celeryworker --since $since --tail 500 2>&1) -join "`n"
        }
        catch {
            $logs = ""
        }
    }

    foreach ($pattern in $knownTransientPatterns) {
        if ([regex]::IsMatch($logs, [regex]::Escape($pattern), [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
            $names = ($FailedDocuments | ForEach-Object { $_.name }) -join ", "
            Write-Output "Transient ApeRAG graph failure detected ($pattern): $names"
            return $true
        }
    }

    return $false
}

function Invoke-GraphRebuild {
    param([object[]]$Documents)

    foreach ($doc in ($Documents | Sort-Object name)) {
        Invoke-ApeRagJson -Method "POST" -Path "/api/v1/collections/$($collection.id)/documents/$($doc.id)/rebuild_indexes" -Body @{
            index_types = @("GRAPH")
        } | Out-Null
        Write-Output "GRAPH rebuild requested: $($doc.name)"
        if ($sequentialGraphRebuild) {
            do {
                Start-Sleep -Seconds $GraphPollSeconds
                $currentDocs = Invoke-ApeRagJson -Method "GET" -Path "/api/v1/collections/$($collection.id)/documents?page=1&page_size=100"
                $currentDoc = $currentDocs.items | Where-Object { $_.id -eq $doc.id } | Select-Object -First 1
                Write-Output "Sequential graph status: $($doc.name)=$($currentDoc.graph_index_status)"
            } while ($currentDoc.graph_index_status -in @("PENDING", "CREATING"))
        }
    }
}

Write-Output "Включение ApeRAG graph для curated memory..."
if ($sequentialGraphRebuild) {
    Write-Output "FreeDeepseekAPI backend detected: graph rebuild will run sequentially to avoid DeepSeek Web parallel chat limits."
}

.\scripts\configure_aperag.ps1 `
    -EnvFile $EnvFile `
    -CompletionBackend $CompletionBackend `
    -CompletionProvider $CompletionProvider `
    -CompletionModel $CompletionModel | Write-Output

$collections = Invoke-ApeRagJson -Method "GET" -Path "/api/v1/collections?page=1&page_size=100"
$collection = $collections.items | Where-Object { $_.title -eq $CollectionTitle } | Select-Object -First 1
if (-not $collection) {
    Write-Error "ApeRAG collection не найдена: $CollectionTitle"
}

$detail = Invoke-ApeRagJson -Method "GET" -Path "/api/v1/collections/$($collection.id)"
$config = ConvertTo-PlainObject $detail.config
$config["enable_knowledge_graph"] = $true
if ($config["embedding"]) {
    $config["embedding"]["tags"] = @()
}
if ($config["completion"]) {
    $config["completion"]["tags"] = @()
}
if (-not $config.Contains("knowledge_graph_config") -or -not $config["knowledge_graph_config"]) {
    $config["knowledge_graph_config"] = @{
        entity_types = @("organization", "person", "event", "technology", "category")
    }
}

Invoke-ApeRagJson -Method "PUT" -Path "/api/v1/collections/$($collection.id)" -Body @{
    title = $detail.title
    description = $detail.description
    config = $config
} | Out-Null

$docs = Invoke-ApeRagJson -Method "GET" -Path "/api/v1/collections/$($collection.id)/documents?page=1&page_size=100"
if (-not $docs.items -or $docs.items.Count -eq 0) {
    Write-Error "ApeRAG collection пуста: $($collection.id)"
}

$docsToRebuild = if ($FullRebuild) {
    @($docs.items)
}
else {
    @($docs.items | Where-Object { $_.graph_index_status -ne "ACTIVE" })
}
if ($docsToRebuild.Count -eq 0) {
    Write-Output "Graph rebuild skipped: all documents already have ACTIVE graph indexes."
}

$graphRebuildStartedAt = Get-Date
Invoke-GraphRebuild -Documents $docsToRebuild

$attempt = 0
while ($true) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        Start-Sleep -Seconds 10
        $docs = Invoke-ApeRagJson -Method "GET" -Path "/api/v1/collections/$($collection.id)/documents?page=1&page_size=100"
        $groups = $docs.items | Group-Object graph_index_status | Sort-Object Name
        $summary = ($groups | ForEach-Object { "$($_.Name)=$($_.Count)" }) -join ", "
        Write-Output "Graph status: $summary"

        $failed = @($docs.items | Where-Object { $_.graph_index_status -eq "FAILED" })
        if ($failed.Count -gt 0) {
            $isTransient = Test-TransientGraphFailure -FailedDocuments $failed -GraphRebuildStartedAt $graphRebuildStartedAt
            if ($attempt -lt $MaxRetries -and ($isTransient -or $failed.Count -gt 0)) {
                $attempt += 1
                if (-not $isTransient) {
                    $names = ($failed | ForEach-Object { $_.name }) -join ", "
                    Write-Output "Retrying failed GRAPH documents without confirmed transient log pattern: $names"
                }
                Write-Output "Повтор ApeRAG graph rebuild: attempt=$attempt/$MaxRetries через $RetryDelaySeconds секунд."
                Start-Sleep -Seconds $RetryDelaySeconds
                $graphRebuildStartedAt = Get-Date
                Invoke-GraphRebuild -Documents $failed
                break
            }

            $failed | Select-Object name,status,graph_index_status | Format-Table -AutoSize
            Write-Error "ApeRAG graph rebuild failed for $($failed.Count) document(s)."
        }

        $ready = @($docs.items | Where-Object { $_.graph_index_status -eq "ACTIVE" })
        if ($ready.Count -eq $docs.items.Count) {
            break
        }
    } while ((Get-Date) -lt $deadline)

    $failed = @($docs.items | Where-Object { $_.graph_index_status -eq "FAILED" })
    $ready = @($docs.items | Where-Object { $_.graph_index_status -eq "ACTIVE" })
    if ($failed.Count -eq 0 -or $ready.Count -eq $docs.items.Count) {
        break
    }
}

$notReady = @($docs.items | Where-Object { $_.graph_index_status -ne "ACTIVE" })
if ($notReady.Count -gt 0) {
    $notReady | Select-Object name,status,graph_index_status | Format-Table -AutoSize
    Write-Error "ApeRAG graph rebuild timeout after $TimeoutSeconds seconds."
}

$failedDocs = @($docs.items | Where-Object { $_.status -eq "FAILED" })
if ($failedDocs.Count -gt 0) {
    $failedDocs | Select-Object name,status,vector_index_status,fulltext_index_status,graph_index_status | Format-Table -AutoSize
    Write-Error "ApeRAG documents still have FAILED status after graph rebuild."
}

$labels = Invoke-ApeRagJson -Method "GET" -Path "/api/v1/collections/$($collection.id)/graphs/labels"
$graph = Invoke-ApeRagJson -Method "GET" -Path "/api/v1/collections/$($collection.id)/graphs?max_nodes=1000&max_depth=3" -TimeoutSec 120

$nodeCount = @($graph.nodes).Count
$edgeCount = @($graph.edges).Count
$labelCount = @($labels.labels).Count
if ($nodeCount -eq 0 -or $edgeCount -eq 0 -or $labelCount -eq 0) {
    Write-Error "ApeRAG curated graph пустой: labels=$labelCount, nodes=$nodeCount, edges=$edgeCount"
}

Write-Output "ApeRAG curated graph OK: labels=$labelCount, nodes=$nodeCount, edges=$edgeCount"
