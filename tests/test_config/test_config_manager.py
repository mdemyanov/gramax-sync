"""Тесты для ConfigManager."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from gramax_sync.config.config_manager import (
    config_exists,
    get_config_dir,
    get_config_path,
    load_config,
    require_config,
    save_config,
)
from gramax_sync.config.local_config import LocalConfig
from gramax_sync.config.models import Catalog, Section, Source


@pytest.fixture
def temp_config_dir(tmp_path):
    """Временная директория для конфигурации."""
    return tmp_path / ".config" / "gramax-sync"


@pytest.fixture
def sample_config():
    """Пример конфигурации."""
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


def test_get_config_path():
    """Тест получения пути к конфигурации."""
    path = get_config_path()
    assert isinstance(path, Path)
    assert path.name == "config.yaml"
    assert ".config" in str(path)
    assert "gramax-sync" in str(path)


def test_get_config_dir():
    """Тест получения директории конфигурации."""
    dir_path = get_config_dir()
    assert isinstance(dir_path, Path)
    assert dir_path.name == "gramax-sync"
    assert ".config" in str(dir_path)


@patch("gramax_sync.config.config_manager.CONFIG_FILE")
def test_config_exists_true(mock_config_file):
    """Тест проверки существования конфигурации (существует)."""
    mock_config_file.exists.return_value = True
    assert config_exists() is True


@patch("gramax_sync.config.config_manager.CONFIG_FILE")
def test_config_exists_false(mock_config_file):
    """Тест проверки существования конфигурации (не существует)."""
    mock_config_file.exists.return_value = False
    assert config_exists() is False


def test_save_config(sample_config, tmp_path, monkeypatch):
    """Тест сохранения конфигурации."""
    # Создаём реальные пути для теста
    config_dir = tmp_path / ".config" / "gramax-sync"
    config_file = config_dir / "config.yaml"

    # Патчим константы модуля
    import gramax_sync.config.config_manager as cm
    monkeypatch.setattr(cm, "CONFIG_FILE", config_file)
    monkeypatch.setattr(cm, "CONFIG_DIR", config_dir)

    with patch("gramax_sync.config.config_manager.console") as mock_console:
        save_config(sample_config)
        assert config_file.exists()
        # Проверяем, что файл содержит правильные данные
        loaded = LocalConfig.from_yaml_string(config_file.read_text())
        assert loaded.repo_url == sample_config.repo_url
        mock_console.print.assert_called()


def test_load_config_yaml(sample_config, tmp_path, monkeypatch):
    """Тест загрузки YAML конфигурации."""
    config_file = tmp_path / "config.yaml"
    config_dir = tmp_path / ".config" / "gramax-sync"
    config_dir.mkdir(parents=True, exist_ok=True)
    yaml_content = sample_config.model_dump_yaml()
    config_file.write_text(yaml_content)

    # Патчим константы модуля
    import gramax_sync.config.config_manager as cm
    monkeypatch.setattr(cm, "CONFIG_FILE", config_file)
    monkeypatch.setattr(cm, "CONFIG_DIR", config_dir)

    with patch("gramax_sync.config.config_manager.console"):
        config = load_config()
        assert config is not None
        assert config.repo_url == sample_config.repo_url
        assert len(config.sections) == 1


@patch("gramax_sync.config.config_manager.CONFIG_FILE")
@patch("gramax_sync.config.config_manager.CONFIG_DIR")
def test_load_config_not_found(mock_config_dir, mock_config_file):
    """Тест загрузки несуществующей конфигурации."""
    mock_config_file.exists.return_value = False
    old_config_file = mock_config_dir / "config.json"
    old_config_file.exists = MagicMock(return_value=False)

    config = load_config()
    assert config is None


def test_load_config_json_migration(tmp_path, monkeypatch):
    """Тест миграции JSON конфигурации в YAML."""
    # Создаём временные файлы
    config_dir = tmp_path / ".config" / "gramax-sync"
    config_dir.mkdir(parents=True, exist_ok=True)
    json_file = config_dir / "config.json"
    yaml_file = config_dir / "config.yaml"

    json_data = {
        "repo_url": "https://gitlab.example.com/repo",
        "config_branch": "main",
        "catalog_branch": "private",
        "base_url": "https://gitlab.example.com",
        "workspace_dir": "~/workspace",
        "sections": [
            {
                "name": "section1",
                "catalogs": [
                    {"name": "catalog1", "source": {"url": "https://gitlab.example.com"}}
                ],
            }
        ],
    }
    json_file.write_text(json.dumps(json_data))

    # Патчим константы модуля
    import gramax_sync.config.config_manager as cm
    monkeypatch.setattr(cm, "CONFIG_FILE", yaml_file)
    monkeypatch.setattr(cm, "CONFIG_DIR", config_dir)

    with patch("gramax_sync.config.config_manager.console") as mock_console:
        with patch("gramax_sync.config.config_manager.save_config") as mock_save:
            config = load_config()
            assert config is not None
            assert config.repo_url == json_data["repo_url"]
            mock_save.assert_called_once()
            assert not json_file.exists()  # Старый файл должен быть удалён
            mock_console.print.assert_called()


@patch("gramax_sync.config.config_manager.load_config")
def test_require_config_success(mock_load_config, sample_config):
    """Тест require_config при успешной загрузке."""
    mock_load_config.return_value = sample_config
    config = require_config()
    assert config == sample_config


@patch("gramax_sync.config.config_manager.load_config")
def test_require_config_not_found(mock_load_config):
    """Тест require_config при отсутствии конфигурации."""
    mock_load_config.return_value = None
    with pytest.raises(FileNotFoundError, match="Конфигурация не найдена"):
        require_config()


def test_load_config_yaml_error(tmp_path, monkeypatch):
    """Тест обработки ошибки при загрузке YAML."""
    config_file = tmp_path / "config.yaml"
    config_dir = tmp_path / ".config" / "gramax-sync"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file.write_text("invalid: yaml: [", encoding="utf-8")
    
    import gramax_sync.config.config_manager as cm
    monkeypatch.setattr(cm, "CONFIG_FILE", config_file)
    monkeypatch.setattr(cm, "CONFIG_DIR", config_dir)
    
    with patch("gramax_sync.config.config_manager.console") as mock_console:
        with pytest.raises(Exception):
            load_config()
        mock_console.print.assert_called()


def test_load_config_json_migration_error(tmp_path, monkeypatch):
    """Тест обработки ошибки при миграции JSON."""
    config_dir = tmp_path / ".config" / "gramax-sync"
    config_dir.mkdir(parents=True, exist_ok=True)
    json_file = config_dir / "config.json"
    yaml_file = config_dir / "config.yaml"
    
    # Создаём невалидный JSON
    json_file.write_text("invalid json", encoding="utf-8")
    
    import gramax_sync.config.config_manager as cm
    monkeypatch.setattr(cm, "CONFIG_FILE", yaml_file)
    monkeypatch.setattr(cm, "CONFIG_DIR", config_dir)
    
    with patch("gramax_sync.config.config_manager.console") as mock_console:
        with pytest.raises(Exception):
            load_config()
        mock_console.print.assert_called()


def test_save_config_error(tmp_path, monkeypatch, sample_config):
    """Тест обработки ошибки при сохранении конфигурации."""
    config_dir = tmp_path / ".config" / "gramax-sync"
    config_file = config_dir / "config.yaml"
    
    import gramax_sync.config.config_manager as cm
    monkeypatch.setattr(cm, "CONFIG_FILE", config_file)
    monkeypatch.setattr(cm, "CONFIG_DIR", config_dir)
    
    # Мокируем ошибку при записи файла
    with patch("gramax_sync.config.config_manager.console") as mock_console:
        with patch("pathlib.Path.open", side_effect=IOError("Permission denied")):
            with pytest.raises(IOError):
                save_config(sample_config)
            mock_console.print.assert_called()

