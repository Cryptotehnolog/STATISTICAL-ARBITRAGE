param(
    [string]$ShortcutName = "Open LightRAG Graph",
    [string]$DesktopPath = [Environment]::GetFolderPath("Desktop")
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$targetScript = Join-Path $PSScriptRoot "open_lightrag_graph.ps1"
$shortcutPath = Join-Path $DesktopPath "$ShortcutName.lnk"

if (-not (Test-Path -LiteralPath $targetScript)) {
    Write-Error "Script viewer-а LightRAG не найден: $targetScript"
}

if (-not (Test-Path -LiteralPath $DesktopPath)) {
    Write-Error "Desktop path не найден: $DesktopPath"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$targetScript`""
$shortcut.WorkingDirectory = $repoRoot
$shortcut.Description = "Открыть локальный viewer графа LightRAG"
$shortcut.IconLocation = "powershell.exe,0"
$shortcut.Save()

Write-Output "Ярлык создан: $shortcutPath"
Write-Output "Он запускает: $targetScript"
