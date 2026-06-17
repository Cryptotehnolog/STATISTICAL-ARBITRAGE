$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    $python = Join-Path $repoRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $python)) {
        $python = Join-Path $repoRoot ".venv/bin/python"
    }
    if (-not (Test-Path -LiteralPath $python)) {
        $python = "python"
    }

    $script = @'
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path.cwd()
TARGETS = [
    Path("src/stat_arb/agents"),
    Path("src/stat_arb/backtest"),
    Path("src/stat_arb/ingestion"),
    Path("src/stat_arb/statistical"),
    Path("src/stat_arb/storage"),
]

violations: list[str] = []

for target in TARGETS:
    for path in sorted((ROOT / target).rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == 'print'
            ):
                violations.append(f"{path.relative_to(ROOT)}:{node.lineno}")

if violations:
    raise SystemExit(
        "Production modules must not use print(); use logging or CLI/script output instead:\n"
        + "\n".join(violations)
    )
'@

    $script | & $python -
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    Write-Output "Проверка отсутствия print() в production modules прошла."
}
finally {
    Pop-Location
}
