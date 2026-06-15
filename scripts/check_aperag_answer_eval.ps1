param(
    [string]$EnvFile = "data\aperag\.env",
    [string]$CollectionTitle = "stat-arb-project-knowledge",
    [Parameter(Mandatory = $true)]
    [string]$Question,
    [Parameter(Mandatory = $true)]
    [string[]]$RequiredFacts,
    [string[]]$ForbiddenClaims = @(),
    [string[]]$Keywords = @(),
    [int]$TopK = 20
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    Write-Output "Answer eval: детерминированная проверка по retrieved ApeRAG context"
    Write-Output "Вопрос: $Question"
    Write-Output "Примечание: это не LLM judge; проверяются обязательные факты и запрещенные утверждения."

    .\scripts\check_aperag_knowledge.ps1 `
        -EnvFile $EnvFile `
        -CollectionTitle $CollectionTitle `
        -Query $Question `
        -Keywords $Keywords `
        -TopK $TopK `
        -ExpectedText $RequiredFacts `
        -ForbiddenText $ForbiddenClaims | Write-Output

    Write-Output "Answer eval OK."
}
finally {
    Pop-Location
}
