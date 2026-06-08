param(
    [string]$ContainerName = "stat-arb-free-qwen",
    [string]$BaseUrl = "http://127.0.0.1:3264/api",
    [string]$Model = "qwen3.7-plus",
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"

# FreeQwenApi OpenAI-compatible endpoints live under /api/health, /api/models,
# and /api/chat/completions.
Write-Output "Проверка FreeQwenApi container: $ContainerName"
$containerId = docker ps --filter "name=^/$ContainerName$" --format "{{.ID}}"
if (-not $containerId) {
    Write-Error "Docker container '$ContainerName' не запущен. Запустите .\scripts\start_free_qwen.ps1 -Build"
}

$healthStatus = docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" $ContainerName
if ($healthStatus -ne "healthy" -and $healthStatus -ne "none") {
    Write-Error "Docker container '$ContainerName' имеет health='$healthStatus'."
}
Write-Output "Docker container OK: $ContainerName ($healthStatus)"

Write-Output "Проверка FreeQwenApi health: $BaseUrl/health"
$health = Invoke-RestMethod -Uri "$BaseUrl/health" -TimeoutSec $TimeoutSeconds
if ($health.ok -ne $true) {
    Write-Error "FreeQwenApi health ok='$($health.ok)'."
}
if ($health.accounts.available -lt 1) {
    Write-Error "FreeQwenApi не имеет доступных аккаунтов. Обновите Qwen login в data\free_qwen\session."
}
Write-Output "Health OK: accounts=$($health.accounts.available)/$($health.accounts.total)"

Write-Output "Проверка FreeQwenApi models endpoint: $BaseUrl/models"
$models = Invoke-RestMethod -Uri "$BaseUrl/models" -TimeoutSec $TimeoutSeconds
$modelIds = @($models.data | ForEach-Object { $_.id })
if ($modelIds -notcontains $Model) {
    Write-Error "Model '$Model' не найден. Доступные модели: $($modelIds -join ', ')"
}
Write-Output "Models endpoint OK: $($modelIds.Count) model(s)"

Write-Output "Проверка FreeQwenApi chat endpoint с model: $Model"
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

$chat = Invoke-WebRequest `
    -UseBasicParsing `
    -Uri "$BaseUrl/chat/completions" `
    -Method Post `
    -ContentType "application/json" `
    -Headers @{ Authorization = "Bearer local-not-secret" } `
    -Body $body `
    -TimeoutSec $TimeoutSeconds

if ($chat.StatusCode -lt 200 -or $chat.StatusCode -ge 300) {
    Write-Error "Chat endpoint вернул HTTP $($chat.StatusCode)."
}
if ($chat.Content -notmatch "OK") {
    Write-Error "Chat endpoint не вернул ожидаемый OK response."
}
Write-Output "Chat endpoint OK"
Write-Output "Проверка FreeQwenApi прошла."
