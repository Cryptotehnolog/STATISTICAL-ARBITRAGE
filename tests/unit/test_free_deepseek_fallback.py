"""Static tests for FreeDeepseekAPI ApeRAG fallback automation."""

from pathlib import Path

DOCKERFILE = Path("infra/free_deepseek/Dockerfile")
COMPOSE = Path("infra/free_deepseek/docker-compose.yml")
START_SCRIPT = Path("scripts/start_free_deepseek.ps1")
CHECK_SCRIPT = Path("scripts/check_free_deepseek.ps1")
GRAPH_SMOKE = Path("scripts/check_aperag_graph_smoke.ps1")
CONFIGURE_APERAG = Path("scripts/configure_aperag.ps1")
SEED_APERAG = Path("scripts/seed_aperag_curated.ps1")
ENABLE_GRAPH = Path("scripts/enable_aperag_curated_graph.ps1")
ENV_EXAMPLE = Path(".env.example")
SECRET_GUARD = Path("scripts/check_secret_leaks.ps1")


def test_free_deepseek_container_is_isolated_and_runtime_auth_is_not_committed() -> None:
    """FreeDeepseekAPI should run in a separate container with auth mounted from data/."""
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    compose = COMPOSE.read_text(encoding="utf-8")
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "ForgetMeAI/FreeDeepseekAPI.git" in dockerfile
    assert "NON_INTERACTIVE=1" in dockerfile
    assert "DEEPSEEK_AUTH_PATH=/runtime/deepseek-auth.json" in dockerfile
    assert "stat-arb-free-deepseek" in compose
    assert "127.0.0.1:9655:9655" in compose
    assert "../../data/free_deepseek:/runtime" in compose
    assert "deepseek-auth.json" in gitignore
    assert ".chrome-for-testing-profile-deepseek/" in gitignore


def test_free_deepseek_scripts_start_and_check_openai_compatible_proxy() -> None:
    """Scripts should start the container and verify health, models, and chat."""
    start_script = START_SCRIPT.read_text(encoding="utf-8")
    check_script = CHECK_SCRIPT.read_text(encoding="utf-8")

    assert "docker compose" in start_script
    assert "infra\\free_deepseek\\docker-compose.yml" in start_script
    assert "data\\free_deepseek" in start_script
    assert "deepseek-auth.json" in start_script
    assert "Write-Error \"DeepSeek auth file не найден" in start_script
    assert "stat-arb-free-deepseek" in check_script
    assert "/health" in check_script
    assert "/v1/models" in check_script
    assert "/v1/chat/completions" in check_script
    assert "deepseek-chat" in check_script
    assert "config_ready" in check_script


def test_aperag_can_select_free_deepseek_completion_backend_explicitly() -> None:
    """ApeRAG scripts should keep OmniRoute default and require explicit fallback selection."""
    configure = CONFIGURE_APERAG.read_text(encoding="utf-8")
    seed = SEED_APERAG.read_text(encoding="utf-8")
    enable_graph = ENABLE_GRAPH.read_text(encoding="utf-8")
    env_example = ENV_EXAMPLE.read_text(encoding="utf-8")

    assert '[ValidateSet("omniroute", "free_deepseek")]' in configure
    assert '$CompletionBackend = "omniroute"' in configure
    assert "stat-arb-free-deepseek" in configure
    assert "http://host.docker.internal:9655/v1" in configure
    assert "deepseek-chat" in configure
    assert "-CompletionBackend $CompletionBackend" in seed
    assert "-CompletionBackend $CompletionBackend" in enable_graph
    assert "APERAG_COMPLETION_BACKEND=omniroute" in env_example
    assert "FREE_DEEPSEEK_BASE_URL=http://127.0.0.1:9655/v1" in env_example


def test_aperag_graph_smoke_can_select_free_deepseek_model() -> None:
    """Small graph smoke should benchmark real ApeRAG extraction with fallback models."""
    graph_smoke = GRAPH_SMOKE.read_text(encoding="utf-8")

    assert '[ValidateSet("omniroute", "free_deepseek")]' in graph_smoke
    assert "[string]$CompletionModel" in graph_smoke
    assert "-CompletionBackend $CompletionBackend" in graph_smoke
    assert "stat-arb-free-deepseek" in graph_smoke
    assert "deepseek-chat" in graph_smoke


def test_secret_guard_blocks_free_deepseek_runtime_auth_files() -> None:
    """DeepSeek Web session files should be guarded like real secrets."""
    guard = SECRET_GUARD.read_text(encoding="utf-8")

    assert "deepseek-auth.json" in guard
    assert "DEEPSEEK_TOKEN" in guard
    assert "DEEPSEEK_COOKIE" in guard
