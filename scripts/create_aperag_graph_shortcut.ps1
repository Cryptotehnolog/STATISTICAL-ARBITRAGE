param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Граф знаний ApeRAG.lnk"
$legacyShortcutPath = Join-Path $desktop "ApeRAG Knowledge Graph.lnk"
$target = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$openScript = Join-Path $repoRoot "scripts\open_aperag_graph.ps1"
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$openScript`" -Port $Port"

if (Test-Path -LiteralPath $legacyShortcutPath) {
    Remove-Item -LiteralPath $legacyShortcutPath -Force
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $repoRoot
$shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,167"
$shortcut.Description = "Запустить локальный 3D-граф знаний ApeRAG"
$shortcut.Save()

Write-Output "Ярлык создан: $shortcutPath"
