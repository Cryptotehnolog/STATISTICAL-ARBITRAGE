param(
    [string]$ContainerName = "stat-arb-free-deepseek",
    [string]$BaseUrl = "http://127.0.0.1:9655",
    [string]$Model = "deepseek-chat",
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"

Write-Output "Проверка FreeDeepseekAPI container: $ContainerName"
$containerId = docker ps --filter "name=^/$ContainerName$" --format "{{.ID}}"
if (-not $containerId) {
    Write-Error "Docker container '$ContainerName' не запущен. Запустите .\scripts\start_free_deepseek.ps1 -Build"
}

$healthStatus = docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" $ContainerName
if ($healthStatus -ne "healthy" -and $healthStatus -ne "none") {
    Write-Error "Docker container '$ContainerName' имеет health='$healthStatus'."
}
Write-Output "Docker container OK: $ContainerName ($healthStatus)"

Write-Output "Проверка FreeDeepseekAPI health: $BaseUrl/health"
$health = Invoke-RestMethod -Uri "$BaseUrl/health" -TimeoutSec $TimeoutSeconds
if ($health.status -ne "ok") {
    Write-Error "FreeDeepseekAPI health status='$($health.status)'."
}
if ($health.config_ready -ne $true) {
    Write-Error "FreeDeepseekAPI config_ready=false. Обновите DeepSeek login и deepseek-auth.json в data\free_deepseek."
}
Write-Output "Health OK: config_ready=$($health.config_ready)"

Write-Output "Проверка FreeDeepseekAPI models endpoint: $BaseUrl/v1/models"
$models = Invoke-RestMethod -Uri "$BaseUrl/v1/models" -TimeoutSec $TimeoutSeconds
$modelIds = @($models.data | ForEach-Object { $_.id })
if ($modelIds -notcontains $Model) {
    Write-Error "Model '$Model' не найден. Доступные модели: $($modelIds -join ', ')"
}
Write-Output "Models endpoint OK: $($modelIds.Count) model(s)"

Write-Output "Проверка FreeDeepseekAPI chat endpoint с model: $Model"
$body = @{
    model = $Model
    messages = @(
        @{
            role = "user"
            content = "Reply with OK only."
        }
    )
    temperature = 0
    max_tokens = 8
    stream = $false
} | ConvertTo-Json -Depth 10

$chat = Invoke-WebRequest `
    -UseBasicParsing `
    -Uri "$BaseUrl/v1/chat/completions" `
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
Write-Output "Проверка FreeDeepseekAPI прошла."
