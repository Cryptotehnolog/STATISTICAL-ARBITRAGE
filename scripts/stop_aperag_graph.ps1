param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

$lines = netstat -ano | Select-String -Pattern "127\.0\.0\.1:$Port\s+.*LISTENING"
$processIds = @()
foreach ($line in $lines) {
    $parts = ($line.ToString().Trim() -split "\s+")
    $processIds += [int]$parts[-1]
}

$processIds = $processIds | Sort-Object -Unique
if (-not $processIds) {
    Write-Output "Сервер графа ApeRAG не запущен на порту $Port."
    return
}

foreach ($processId in $processIds) {
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
}

Write-Output "Сервер графа ApeRAG остановлен: port=$Port, processes=$($processIds -join ',')"
