"""Тесты для команды edit."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from gramax_sync.cli.edit import edit
import sys
edit_module = sys.modules['gramax_sync.cli.edit']
from gramax_sync.config.local_config import LocalConfig
from gramax_sync.config.models import Catalog, Section, Source


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
def runner():
    """CLI runner для тестов."""
    return CliRunner()


@patch.object(edit_module, "load_config")
def test_edit_show_success(mock_load_config, runner, sample_config):
    """Тест команды edit show при успешной загрузке."""
    mock_load_config.return_value = sample_config

    result = runner.invoke(edit, ["show"])
    assert result.exit_code == 0
    assert "Текущая локальная конфигурация" in result.output
    assert "test-section" in result.output


@patch.object(edit_module, "load_config")
def test_edit_show_no_config(mock_load_config, runner):
    """Тест команды edit show при отсутствии конфигурации."""
    mock_load_config.return_value = None

    result = runner.invoke(edit, ["show"])
    assert result.exit_code != 0
    assert "Конфигурация не найдена" in result.output


@patch.object(edit_module, "save_config")
@patch.object(edit_module, "load_config")
def test_edit_add_section(mock_load_config, mock_save_config, runner, sample_config):
    """Тест добавления секции через параметры."""
    mock_load_config.return_value = sample_config

    result = runner.invoke(edit, ["add", "--section", "new-section"])
    assert result.exit_code == 0
    assert "добавлена" in result.output.lower()
    mock_save_config.assert_called_once()


@patch.object(edit_module, "save_config")
@patch.object(edit_module, "load_config")
def test_edit_add_catalog(mock_load_config, mock_save_config, runner, sample_config):
    """Тест добавления каталога через параметры."""
    mock_load_config.return_value = sample_config

    result = runner.invoke(
        edit,
        [
            "add",
            "--section",
            "test-section",
            "--catalog",
            "new-catalog",
            "--source-url",
            "https://gitlab.example.com",
        ],
    )
    assert result.exit_code == 0
    assert "добавлен" in result.output.lower()
    mock_save_config.assert_called_once()


@patch.object(edit_module, "load_config")
def test_edit_add_section_duplicate(mock_load_config, runner, sample_config):
    """Тест добавления дублирующейся секции."""
    mock_load_config.return_value = sample_config

    result = runner.invoke(edit, ["add", "--section", "test-section"])
    assert result.exit_code != 0
    assert "уже существует" in result.output.lower() or "error" in result.output.lower()


@patch.object(edit_module, "save_config")
@patch.object(edit_module, "load_config")
def test_edit_remove_catalog(mock_load_config, mock_save_config, runner, sample_config):
    """Тест удаления каталога."""
    mock_load_config.return_value = sample_config

    result = runner.invoke(
        edit, ["remove", "--section", "test-section", "--catalog", "test-catalog", "--force"]
    )
    assert result.exit_code == 0
    assert "удалён" in result.output.lower()
    mock_save_config.assert_called_once()


@patch.object(edit_module, "save_config")
@patch.object(edit_module, "load_config")
def test_edit_remove_section(mock_load_config, mock_save_config, runner, sample_config):
    """Тест удаления секции."""
    mock_load_config.return_value = sample_config

    result = runner.invoke(edit, ["remove", "--section", "test-section", "--force"])
    assert result.exit_code == 0
    assert "удалена" in result.output.lower()
    mock_save_config.assert_called_once()


@patch.object(edit_module, "load_config")
def test_edit_remove_not_found(mock_load_config, runner, sample_config):
    """Тест удаления несуществующего элемента."""
    mock_load_config.return_value = sample_config

    result = runner.invoke(
        edit, ["remove", "--section", "nonexistent", "--catalog", "nonexistent", "--force"]
    )
    assert result.exit_code != 0
    assert "не найден" in result.output.lower()


@patch.object(edit_module, "load_config")
def test_edit_no_config(mock_load_config, runner):
    """Тест команд edit при отсутствии конфигурации."""
    mock_load_config.return_value = None

    result = runner.invoke(edit, ["add", "--section", "test"])
    assert result.exit_code != 0
    assert "Конфигурация не найдена" in result.output

