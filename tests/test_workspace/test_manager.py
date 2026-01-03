"""Тесты для управления workspace."""

import tempfile
from pathlib import Path

import pytest

from gramax_sync.config.models import Workspace
from gramax_sync.workspace.manager import (
    ensure_workspace_structure,
    get_repository_path,
    list_repositories,
)


def test_ensure_workspace_structure(sample_workspace_data, tmp_path):
    """Тест создания структуры workspace."""
    # Используем временную директорию
    sample_workspace_data["workspace_dir"] = str(tmp_path / "workspace")
    workspace = Workspace(**sample_workspace_data)

    ensure_workspace_structure(workspace)

    # Проверяем, что директории созданы
    workspace_path = Path(workspace.workspace_dir)
    assert workspace_path.exists()
    assert (workspace_path / "section1").exists()
    assert (workspace_path / "section1" / "catalog1").exists()


def test_get_repository_path(sample_workspace_data):
    """Тест формирования пути к репозиторию."""
    workspace = Workspace(**sample_workspace_data)
    path = get_repository_path(workspace, "section1", "catalog1")

    assert path == Path(workspace.workspace_dir) / "section1" / "catalog1"


def test_get_repository_path_invalid_section(sample_workspace_data):
    """Тест формирования пути с несуществующей секцией."""
    workspace = Workspace(**sample_workspace_data)
    with pytest.raises(ValueError, match="Секция 'invalid' не найдена"):
        get_repository_path(workspace, "invalid", "catalog1")


def test_get_repository_path_invalid_catalog(sample_workspace_data):
    """Тест формирования пути с несуществующим каталогом."""
    workspace = Workspace(**sample_workspace_data)
    with pytest.raises(ValueError, match="Каталог 'invalid' не найден"):
        get_repository_path(workspace, "section1", "invalid")


def test_list_repositories(sample_workspace_data):
    """Тест получения списка репозиториев."""
    workspace = Workspace(**sample_workspace_data)
    repositories = list_repositories(workspace)

    assert len(repositories) == 1
    section_name, catalog_name, path = repositories[0]
    assert section_name == "section1"
    assert catalog_name == "catalog1"
    assert path == Path(workspace.workspace_dir) / "section1" / "catalog1"


def test_list_repositories_multiple(sample_workspace_data):
    """Тест получения списка репозиториев с несколькими секциями."""
    sample_workspace_data["sections"].append(
        {
            "name": "section2",
            "catalogs": [
                {
                    "name": "catalog2",
                    "source": {"url": "https://gitlab.example.com"},
                },
                {
                    "name": "catalog3",
                    "source": {"url": "https://gitlab.example.com"},
                },
            ],
        }
    )
    workspace = Workspace(**sample_workspace_data)
    repositories = list_repositories(workspace)

    assert len(repositories) == 3
