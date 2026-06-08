param(
    [string]$ContainerName = "omniroute",
    [string[]]$ForbiddenConnectionIds = @(
        "fc868537-fd75-42c6-9b8f-051196f1ed3c",
        "02402742-c217-4167-907f-ec358477ba80",
        "2fda8409-2145-4f72-8df5-f130843589a8",
        "a6868470-cc9c-4d3d-b4e2-14b933b87aae"
    ),
    [switch]$AllowMyAiCombo
)

$ErrorActionPreference = "Stop"

Write-Output "Проверка OmniRoute state: $ContainerName"

$containerId = docker ps -a --filter "name=^/$ContainerName$" --format "{{.ID}}"
if (-not $containerId) {
    Write-Error "Docker container '$ContainerName' не найден."
}

$tempDb = Join-Path $env:TEMP "omniroute-state-check-$([guid]::NewGuid()).sqlite"
try {
    docker cp "${ContainerName}:/app/data/storage.sqlite" $tempDb | Out-Null
    if (-not (Test-Path $tempDb)) {
        Write-Error "Не удалось скопировать OmniRoute storage.sqlite для проверки."
    }

    $env:OMNIROUTE_STATE_DB = $tempDb
    $env:OMNIROUTE_FORBIDDEN_IDS = ($ForbiddenConnectionIds -join ",")
    $env:OMNIROUTE_ALLOW_MY_AI = if ($AllowMyAiCombo) { "1" } else { "0" }

    $pythonScript = @'
import json
import os
import sqlite3
import sys

db_path = os.environ["OMNIROUTE_STATE_DB"]
forbidden_ids = [
    item.strip()
    for item in os.environ.get("OMNIROUTE_FORBIDDEN_IDS", "").split(",")
    if item.strip()
]
allow_my_ai = os.environ.get("OMNIROUTE_ALLOW_MY_AI") == "1"

connection_patterns = ["kiro"] + forbidden_ids

def like_any(column):
    return " or ".join([f"{column} like ?" for _ in connection_patterns])

def params():
    return [f"%{item}%" for item in connection_patterns]

checks = {}
with sqlite3.connect(db_path) as con:
    cur = con.cursor()

    my_ai_clause = "0" if allow_my_ai else "lower(name) = 'my-ai'"
    checks["combos_with_stale_kiro_or_my_ai"] = cur.execute(
        f"""
        select count(*)
        from combos
        where {my_ai_clause}
           or {like_any("data")}
        """,
        params(),
    ).fetchone()[0]

    checks["session_account_affinity_kiro"] = cur.execute(
        "select count(*) from session_account_affinity where provider = 'kiro'"
    ).fetchone()[0]

    checks["key_value_kiro"] = cur.execute(
        f"""
        select count(*)
        from key_value
        where key like '%kiro%'
           or {like_any("value")}
        """,
        params(),
    ).fetchone()[0]

    checks["usage_history_kiro"] = cur.execute(
        """
        select count(*)
        from usage_history
        where provider = 'kiro'
           or model like 'kiro/%'
        """
    ).fetchone()[0]

    checks["call_logs_kiro_or_my_ai"] = cur.execute(
        """
        select count(*)
        from call_logs
        where provider = 'kiro'
           or model like 'kiro/%'
           or requested_model like 'kiro/%'
           or model = 'my-ai'
           or requested_model = 'my-ai'
        """
    ).fetchone()[0]

    checks["semantic_cache_kiro_or_my_ai"] = cur.execute(
        """
        select count(*)
        from semantic_cache
        where model = 'my-ai'
           or model like 'kiro/%'
           or response like '%kiro%'
        """
    ).fetchone()[0]

print(json.dumps(checks, ensure_ascii=False, indent=2))
failed = {key: value for key, value in checks.items() if value}
if failed:
    print("Найдены stale OmniRoute записи:", json.dumps(failed, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)
'@

    $pythonScript | python -
    Write-Output "OmniRoute state OK: stale Kiro/my-ai привязки не найдены."
}
finally {
    if (Test-Path $tempDb) {
        Remove-Item -LiteralPath $tempDb -Force
    }
    Remove-Item Env:\OMNIROUTE_STATE_DB -ErrorAction SilentlyContinue
    Remove-Item Env:\OMNIROUTE_FORBIDDEN_IDS -ErrorAction SilentlyContinue
    Remove-Item Env:\OMNIROUTE_ALLOW_MY_AI -ErrorAction SilentlyContinue
}
