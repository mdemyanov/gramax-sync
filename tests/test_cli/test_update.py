"""Тесты для команды update."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from gramax_sync.cli.update import update
import sys
update_module = sys.modules['gramax_sync.cli.update']
from gramax_sync.config.local_config import LocalConfig
from gramax_sync.config.models import Catalog, Section, Source, Workspace
from gramax_sync.gitlab.exceptions import GitLabError


@pytest.fixture
def sample_config():
    """Пример конфигурации для тестов."""
    source = Source(url="https://gitlab.example.com")
    catalog = Catalog(name="test-catalog", source=source)
    section = Section(name="test-section", catalogs=[catalog])

    return LocalConfig(
        repo_url="https://gitlab.example.com/ritm-authors/gramax-yaml-manager",
        config_branch="main",
        catalog_branch="private",
        base_url="https://gitlab.example.com",
        workspace_dir="~/ritm-workspace",
        sections=[section],
    )


@pytest.fixture
def sample_workspace():
    """Пример workspace для тестов."""
    source = Source(url="https://gitlab.example.com")
    catalog1 = Catalog(name="test-catalog", source=source)
    catalog2 = Catalog(name="new-catalog", source=source)
    section1 = Section(name="test-section", catalogs=[catalog1])
    section2 = Section(name="new-section", catalogs=[catalog2])

    return Workspace(
        workspace_dir="~/ritm-workspace",
        sections=[section1, section2],
    )


@pytest.fixture
def runner():
    """CLI runner для тестов."""
    return CliRunner()


@patch.object(update_module, "save_config")
@patch.object(update_module, "load_workspace_from_string")
@patch.object(update_module, "GitLabClient")
@patch.object(update_module, "TokenManager")
@patch.object(update_module, "load_config")
def test_update_success(
    mock_load_config,
    mock_token_manager_class,
    mock_gitlab_client_class,
    mock_load_workspace,
    mock_save_config,
    runner,
    sample_config,
    sample_workspace,
):
    """Тест успешного обновления конфигурации."""
    mock_load_config.return_value = sample_config
    
    mock_token_manager_instance = MagicMock()
    mock_token_manager_instance.get_token.return_value = "test-token"
    mock_token_manager_class.return_value = mock_token_manager_instance

    mock_client = MagicMock()
    mock_client.get_workspace_file.return_value = "workspace yaml content"
    mock_gitlab_client_class.return_value = mock_client

    mock_load_workspace.return_value = sample_workspace

    result = runner.invoke(update, ["--force"])
    assert result.exit_code == 0
    assert "обновлена" in result.output.lower()
    mock_save_config.assert_called_once()


@patch.object(update_module, "load_config")
def test_update_no_config(mock_load_config, runner):
    """Тест обновления при отсутствии конфигурации."""
    mock_load_config.return_value = None

    result = runner.invoke(update)
    assert result.exit_code != 0
    assert "Конфигурация не найдена" in result.output


@patch.object(update_module, "GitLabClient")
@patch.object(update_module, "TokenManager")
@patch.object(update_module, "load_config")
def test_update_gitlab_error(
    mock_load_config, mock_token_manager_class, mock_gitlab_client_class, runner, sample_config
):
    """Тест обработки ошибки GitLab."""
    mock_load_config.return_value = sample_config
    
    mock_token_manager_instance = MagicMock()
    mock_token_manager_instance.get_token.return_value = "test-token"
    mock_token_manager_class.return_value = mock_token_manager_instance

    mock_client = MagicMock()
    mock_client.get_workspace_file.side_effect = GitLabError("Ошибка доступа")
    mock_gitlab_client_class.return_value = mock_client

    result = runner.invoke(update, ["--force"])
    assert result.exit_code != 0
    assert "Ошибка" in result.output


@patch.object(update_module, "load_workspace_from_string")
@patch.object(update_module, "GitLabClient")
@patch.object(update_module, "TokenManager")
@patch.object(update_module, "load_config")
def test_update_preserves_selected_sections(
    mock_load_config,
    mock_token_manager_class,
    mock_gitlab_client_class,
    mock_load_workspace,
    runner,
    sample_config,
    sample_workspace,
):
    """Тест сохранения выбранных секций при обновлении."""
    mock_load_config.return_value = sample_config
    
    mock_token_manager_instance = MagicMock()
    mock_token_manager_instance.get_token.return_value = "test-token"
    mock_token_manager_class.return_value = mock_token_manager_instance

    mock_client = MagicMock()
    mock_client.get_workspace_file.return_value = "workspace yaml content"
    mock_gitlab_client_class.return_value = mock_client

    mock_load_workspace.return_value = sample_workspace

    with patch.object(update_module, "save_config") as mock_save:
        result = runner.invoke(update, ["--force"])
        assert result.exit_code == 0
        # Проверяем, что сохранена только существующая секция
        saved_config = mock_save.call_args[0][0]
        assert len(saved_config.sections) == 1
        assert saved_config.sections[0].name == "test-section"

