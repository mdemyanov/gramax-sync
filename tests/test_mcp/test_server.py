"""Тесты для MCP сервера."""

from unittest.mock import MagicMock, patch

import pytest

from gramax_sync.mcp.server import get_mcp_config, mcp, require_mcp_config


def test_mcp_server_initialized():
    """Проверка инициализации MCP сервера."""
    assert mcp is not None
    assert mcp.name == "gramax-sync"


def test_get_mcp_config_from_env(monkeypatch, tmp_path):
    """Проверка загрузки конфигурации из переменной окружения."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("workspace_dir: /tmp/test\nsections: []")
    
    monkeypatch.setenv("GRAMAX_WORKSPACE_PATH", str(config_file))
    
    result = get_mcp_config()
    assert result == config_file


def test_get_mcp_config_not_found(monkeypatch):
    """Проверка обработки отсутствия конфигурации."""
    monkeypatch.delenv("GRAMAX_WORKSPACE_PATH", raising=False)
    
    with patch("gramax_sync.mcp.server.load_config", return_value=None):
        result = get_mcp_config()
        assert result is None


def test_require_mcp_config_success():
    """Проверка успешной загрузки конфигурации."""
    from gramax_sync.config.local_config import LocalConfig
    
    mock_config = LocalConfig(
        repo_url="https://gitlab.example.com/config-repo",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test",
        catalog_branch="private",
        sections=[],
    )
    
    with patch("gramax_sync.mcp.server.load_config", return_value=mock_config):
        result = require_mcp_config()
        assert result == mock_config


def test_require_mcp_config_not_found():
    """Проверка ошибки при отсутствии конфигурации."""
    with patch("gramax_sync.mcp.server.load_config", return_value=None):
        with pytest.raises(FileNotFoundError) as exc_info:
            require_mcp_config()
        
        assert "Конфигурация не найдена" in str(exc_info.value)


def test_get_mcp_config_from_load_config(monkeypatch, tmp_path):
    """Проверка загрузки конфигурации через load_config."""
    from gramax_sync.config.local_config import LocalConfig
    from gramax_sync.config.config_manager import CONFIG_FILE
    
    monkeypatch.delenv("GRAMAX_WORKSPACE_PATH", raising=False)
    
    mock_config = LocalConfig(
        repo_url="https://gitlab.example.com/config-repo",
        base_url="https://gitlab.example.com",
        workspace_dir="/tmp/test",
        catalog_branch="private",
        sections=[],
    )
    
    with patch("gramax_sync.mcp.server.load_config", return_value=mock_config):
        result = get_mcp_config()
        assert result == CONFIG_FILE


def test_get_mcp_config_load_config_exception(monkeypatch):
    """Проверка обработки исключения при загрузке конфигурации."""
    monkeypatch.delenv("GRAMAX_WORKSPACE_PATH", raising=False)
    
    with patch("gramax_sync.mcp.server.load_config", side_effect=Exception("Config error")):
        result = get_mcp_config()
        assert result is None

