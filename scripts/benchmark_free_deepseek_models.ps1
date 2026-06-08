param(
    [string]$BaseUrl = "http://127.0.0.1:9655",
    [string[]]$Models = @(
        "deepseek-chat",
        "deepseek-v3",
        "deepseek-default",
        "deepseek-reasoner",
        "deepseek-r1",
        "deepseek-expert",
        "deepseek-v4-pro"
    ),
    [string]$OutputPath = "data\free_deepseek\model_benchmark.json",
    [int]$TimeoutSeconds = 120,
    [int]$ParallelRequests = 2,
    [switch]$IncludeParallelProbe
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$outputFile = Join-Path $repoRoot $OutputPath
$outputDir = Split-Path -Parent $outputFile

if (-not (Test-Path -LiteralPath $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

function Invoke-ModelChat {
    param(
        [string]$Model,
        [string]$Prompt
    )

    $body = @{
        model = $Model
        messages = @(
            @{
                role = "user"
                content = $Prompt
            }
        )
        temperature = 0
        max_tokens = 32
        stream = $false
    } | ConvertTo-Json -Depth 10

    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $response = Invoke-WebRequest `
            -UseBasicParsing `
            -Uri "$BaseUrl/v1/chat/completions" `
            -Method Post `
            -ContentType "application/json" `
            -Headers @{ Authorization = "Bearer local-not-secret" } `
            -Body $body `
            -TimeoutSec $TimeoutSeconds
        $timer.Stop()

        return [ordered]@{
            ok = $true
            seconds = [math]::Round($timer.Elapsed.TotalSeconds, 3)
            status_code = [int]$response.StatusCode
            error = $null
        }
    }
    catch {
        $timer.Stop()
        return [ordered]@{
            ok = $false
            seconds = [math]::Round($timer.Elapsed.TotalSeconds, 3)
            status_code = $null
            error = $_.Exception.Message
        }
    }
}

function Invoke-ParallelProbe {
    param([string]$Model)

    $scriptBlock = {
        param($BaseUrl, $Model, $TimeoutSeconds)

        $body = @{
            model = $Model
            messages = @(
                @{
                    role = "user"
                    content = "Reply with OK only."
                }
            )
            temperature = 0
            max_tokens = 16
            stream = $false
        } | ConvertTo-Json -Depth 10

        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        try {
            $response = Invoke-WebRequest `
                -UseBasicParsing `
                -Uri "$BaseUrl/v1/chat/completions" `
                -Method Post `
                -ContentType "application/json" `
                -Headers @{ Authorization = "Bearer local-not-secret" } `
                -Body $body `
                -TimeoutSec $TimeoutSeconds
            $timer.Stop()
            [ordered]@{
                ok = $true
                seconds = [math]::Round($timer.Elapsed.TotalSeconds, 3)
                status_code = [int]$response.StatusCode
                error = $null
            }
        }
        catch {
            $timer.Stop()
            [ordered]@{
                ok = $false
                seconds = [math]::Round($timer.Elapsed.TotalSeconds, 3)
                status_code = $null
                error = $_.Exception.Message
            }
        }
    }

    $jobs = for ($i = 0; $i -lt $ParallelRequests; $i += 1) {
        Start-Job -ScriptBlock $scriptBlock -ArgumentList $BaseUrl, $Model, $TimeoutSeconds
    }
    $results = @($jobs | Wait-Job | Receive-Job)
    $jobs | Remove-Job

    $combinedErrors = ($results | Where-Object { -not $_.ok } | ForEach-Object { $_.error }) -join "`n"
    $parallelLimitDetected = $combinedErrors -match "parallel_chat_limit" -or
        $combinedErrors -match "Сообщение генерируется"

    return [ordered]@{
        requested = $ParallelRequests
        ok_count = @($results | Where-Object { $_.ok }).Count
        failed_count = @($results | Where-Object { -not $_.ok }).Count
        parallel_chat_limit_detected = [bool]$parallelLimitDetected
        results = $results
    }
}

Write-Output "Benchmark FreeDeepseekAPI models: $($Models -join ', ')"
if (-not $IncludeParallelProbe) {
    Write-Output "Параллельная проверка отключена. Добавьте -IncludeParallelProbe, чтобы явно проверить parallel_chat_limit."
}

$benchmark = foreach ($model in $Models) {
    Write-Host "Model: $model"
    $chat = Invoke-ModelChat -Model $model -Prompt "Reply with OK only."
    $parallel = $null
    if ($IncludeParallelProbe) {
        $parallel = Invoke-ParallelProbe -Model $model
    }

    [ordered]@{
        model = $model
        chat = $chat
        parallel = $parallel
    }
}

$payload = [ordered]@{
    created_at = (Get-Date).ToUniversalTime().ToString("o")
    base_url = $BaseUrl
    include_parallel_probe = [bool]$IncludeParallelProbe
    models = $benchmark
}

$payload | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $outputFile -Encoding UTF8
Write-Output "Benchmark сохранен: $outputFile"

$benchmark | ForEach-Object {
    $parallelText = if ($_.parallel) {
        "parallel_ok=$($_.parallel.ok_count)/$($_.parallel.requested), parallel_limit=$($_.parallel.parallel_chat_limit_detected)"
    }
    else {
        "parallel=skipped"
    }
    Write-Output "$($_.model): chat_ok=$($_.chat.ok), seconds=$($_.chat.seconds), $parallelText"
}
