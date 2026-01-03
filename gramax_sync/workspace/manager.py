"""Управление структурой workspace."""

from pathlib import Path

from gramax_sync.config.models import Workspace


def ensure_workspace_structure(workspace: Workspace) -> None:
    """Создать структуру директорий workspace.

    Создаёт структуру директорий {workspace_dir}/{section}/{catalog}/ для всех
    секций и каталогов в конфигурации.

    Args:
        workspace: Объект Workspace с конфигурацией

    Raises:
        OSError: Если не удалось создать директории
    """
    workspace_path = Path(workspace.workspace_dir).expanduser()
    workspace_path.mkdir(parents=True, exist_ok=True)

    for section in workspace.sections:
        section_path = workspace_path / section.name
        section_path.mkdir(parents=True, exist_ok=True)

        for catalog in section.catalogs:
            catalog_path = section_path / catalog.name
            catalog_path.mkdir(parents=True, exist_ok=True)


def get_repository_path(workspace: Workspace, section: str, catalog: str) -> Path:
    """Получить путь к репозиторию.

    Args:
        workspace: Объект Workspace с конфигурацией
        section: Имя секции
        catalog: Имя каталога

    Returns:
        Path к директории репозитория

    Raises:
        ValueError: Если секция или каталог не найдены в конфигурации
    """
    workspace_path = Path(workspace.workspace_dir).expanduser()

    # Проверяем существование секции
    section_obj = None
    for s in workspace.sections:
        if s.name == section:
            section_obj = s
            break

    if section_obj is None:
        raise ValueError(f"Секция '{section}' не найдена в конфигурации")

    # Проверяем существование каталога
    catalog_obj = None
    for c in section_obj.catalogs:
        if c.name == catalog:
            catalog_obj = c
            break

    if catalog_obj is None:
        raise ValueError(f"Каталог '{catalog}' не найден в секции '{section}'")

    return workspace_path / section / catalog


def list_repositories(workspace: Workspace) -> list[tuple[str, str, Path]]:
    """Получить список всех репозиториев.

    Args:
        workspace: Объект Workspace с конфигурацией

    Returns:
        Список кортежей (section_name, catalog_name, path) для каждого репозитория
    """
    repositories = []
    workspace_path = Path(workspace.workspace_dir).expanduser()

    for section in workspace.sections:
        for catalog in section.catalogs:
            repo_path = workspace_path / section.name / catalog.name
            repositories.append((section.name, catalog.name, repo_path))

    return repositories
