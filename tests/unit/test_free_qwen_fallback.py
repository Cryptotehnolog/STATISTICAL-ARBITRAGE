"""Static tests for FreeQwenApi ApeRAG fallback automation."""

from pathlib import Path

DOCKERFILE = Path("infra/free_qwen/Dockerfile")
COMPOSE = Path("infra/free_qwen/docker-compose.yml")
START_SCRIPT = Path("scripts/start_free_qwen.ps1")
CHECK_SCRIPT = Path("scripts/check_free_qwen.ps1")
CONFIGURE_APERAG = Path("scripts/configure_aperag.ps1")
SEED_APERAG = Path("scripts/seed_aperag_curated.ps1")
ENABLE_GRAPH = Path("scripts/enable_aperag_curated_graph.ps1")
GRAPH_SMOKE = Path("scripts/check_aperag_graph_smoke.ps1")
ENV_EXAMPLE = Path(".env.example")
SECRET_GUARD = Path("scripts/check_secret_leaks.ps1")


def test_free_qwen_container_is_isolated_and_runtime_session_is_not_committed() -> None:
    """FreeQwenApi should run separately with session mounted from ignored data/."""
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    compose = COMPOSE.read_text(encoding="utf-8")
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "ForgetMeAI/FreeQwenApi.git" in dockerfile
    assert "CHROME_PATH=/usr/bin/chromium" in dockerfile
    assert "SKIP_ACCOUNT_MENU=true" in dockerfile
    assert "stat-arb-free-qwen" in compose
    assert "127.0.0.1:3264:3264" in compose
    assert "../../data/free_qwen/session:/app/session" in compose
    assert "data/free_qwen/session/" in gitignore
    assert "data/free_qwen/logs/" in gitignore


def test_free_qwen_scripts_start_and_check_openai_compatible_proxy() -> None:
    """Scripts should start the container and verify health, models, and chat."""
    start_script = START_SCRIPT.read_text(encoding="utf-8")
    check_script = CHECK_SCRIPT.read_text(encoding="utf-8")

    assert "docker compose" in start_script
    assert "infra\\free_qwen\\docker-compose.yml" in start_script
    assert "data\\free_qwen\\session\\tokens.json" in start_script
    assert "Qwen session tokens не найдены" in start_script
    assert "stat-arb-free-qwen" in check_script
    assert "/api/health" in check_script
    assert "/api/models" in check_script
    assert "/api/chat/completions" in check_script
    assert "qwen3.7-plus" in check_script


def test_aperag_can_select_free_qwen_completion_backend_explicitly() -> None:
    """ApeRAG scripts should support FreeQwenApi only through explicit backend selection."""
    configure = CONFIGURE_APERAG.read_text(encoding="utf-8")
    seed = SEED_APERAG.read_text(encoding="utf-8")
    enable_graph = ENABLE_GRAPH.read_text(encoding="utf-8")
    graph_smoke = GRAPH_SMOKE.read_text(encoding="utf-8")
    env_example = ENV_EXAMPLE.read_text(encoding="utf-8")

    assert '[ValidateSet("omniroute", "free_deepseek", "free_qwen")]' in configure
    assert '$CompletionBackend = "omniroute"' in configure
    assert "stat-arb-free-qwen" in configure
    assert "http://host.docker.internal:3264/api" in configure
    assert "qwen3.7-plus" in configure
    assert "-CompletionBackend $CompletionBackend" in seed
    assert "-CompletionBackend $CompletionBackend" in enable_graph
    assert "-CompletionBackend $CompletionBackend" in graph_smoke
    assert "FREE_QWEN_BASE_URL=http://127.0.0.1:3264/api" in env_example


def test_secret_guard_blocks_free_qwen_runtime_session_files() -> None:
    """Qwen session files should be guarded like real secrets."""
    guard = SECRET_GUARD.read_text(encoding="utf-8")

    assert "data/free_qwen/session" in guard
    assert "tokens.json" in guard
    assert "Authorization.txt" in guard
