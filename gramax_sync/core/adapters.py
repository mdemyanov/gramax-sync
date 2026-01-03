"""Адаптеры для существующих функций, реализующие протоколы."""

from pathlib import Path

from gramax_sync.config.local_config import LocalConfig
from gramax_sync.config.models import Workspace
from gramax_sync.core.protocols import (
    ConfigManagerProtocol,
    GitOperationsProtocol,
    WorkspaceManagerProtocol,
)
from gramax_sync.git import operations as git_operations_module
from gramax_sync.git import status as git_status_module
from gramax_sync.workspace import manager as workspace_manager_module


class ConfigManagerAdapter:
    """Адаптер для функций config_manager, реализующий ConfigManagerProtocol."""

    def require_config(self) -> LocalConfig:
        """Загрузить конфигурацию или выбросить исключение.

        Returns:
            Объект LocalConfig

        Raises:
            FileNotFoundError: Если конфигурация не найдена
        """
        from gramax_sync.config.config_manager import require_config

        return require_config()

    def load_config(self) -> LocalConfig | None:
        """Загрузить локальную конфигурацию из файла.

        Returns:
            Объект LocalConfig или None если файл не найден
        """
        from gramax_sync.config.config_manager import load_config

        return load_config()

    def save_config(self, config: LocalConfig) -> None:
        """Сохранить локальную конфигурацию в файл.

        Args:
            config: Объект LocalConfig для сохранения
        """
        from gramax_sync.config.config_manager import save_config

        save_config(config)


class WorkspaceManagerAdapter:
    """Адаптер для функций workspace.manager, реализующий WorkspaceManagerProtocol."""

    def list_repositories(self, workspace: Workspace) -> list[tuple[str, str, Path]]:
        """Получить список всех репозиториев.

        Args:
            workspace: Объект Workspace с конфигурацией

        Returns:
            Список кортежей (section_name, catalog_name, path) для каждого репозитория
        """
        return workspace_manager_module.list_repositories(workspace)

    def ensure_workspace_structure(self, workspace: Workspace) -> None:
        """Создать структуру директорий workspace.

        Args:
            workspace: Объект Workspace с конфигурацией

        Raises:
            OSError: Если не удалось создать директории
        """
        workspace_manager_module.ensure_workspace_structure(workspace)


class GitOperationsAdapter:
    """Адаптер для функций git.operations и git.status, реализующий GitOperationsProtocol."""

    def clone_repository(self, url: str, path: Path, branch: str) -> None:
        """Клонировать репозиторий.

        Args:
            url: URL репозитория для клонирования
            path: Путь к директории, куда клонировать
            branch: Ветка для переключения после клонирования

        Raises:
            GitCommandError: Если клонирование не удалось
            OSError: Если не удалось создать директорию
        """
        git_operations_module.clone_repository(url, path, branch)

    def pull_repository(self, path: Path, branch: str) -> None:
        """Обновить репозиторий.

        Args:
            path: Путь к репозиторию
            branch: Ветка для обновления

        Raises:
            InvalidGitRepositoryError: Если путь не является Git репозиторием
            GitCommandError: Если pull не удался (например, конфликты)
            FileNotFoundError: Если репозиторий не существует
        """
        git_operations_module.pull_repository(path, branch)

    def get_repository_status(self, path: Path) -> str:
        """Получить статус репозитория.

        Args:
            path: Путь к репозиторию

        Returns:
            Статус репозитория (clean, modified, ahead, behind, diverged, error, not_found)
        """
        return git_status_module.get_repository_status(path)

    def commit_repository(
        self,
        path: Path,
        message: str | None = None,
        add_all: bool = True,
    ) -> str | None:
        """Закоммитить изменения в репозитории.

        Args:
            path: Путь к репозиторию
            message: Сообщение коммита (если None, генерируется автоматически)
            add_all: Добавлять ли все файлы перед коммитом

        Returns:
            Хеш коммита или None если нет изменений для коммита

        Raises:
            InvalidGitRepositoryError: Если путь не является Git репозиторием
            GitCommandError: Если commit не удался
            FileNotFoundError: Если репозиторий не существует
        """
        return git_operations_module.commit_repository(path, message, add_all)

    def push_repository(
        self,
        path: Path,
        branch: str,
        force: bool = False,
        set_upstream: bool = False,
    ) -> int | None:
        """Отправить изменения в remote.

        Args:
            path: Путь к репозиторию
            branch: Ветка для отправки
            force: Использовать force push
            set_upstream: Установить upstream для новой ветки

        Returns:
            Количество отправленных коммитов или None если нечего отправлять

        Raises:
            InvalidGitRepositoryError: Если путь не является Git репозиторием
            GitCommandError: Если push не удался
            FileNotFoundError: Если репозиторий не существует
        """
        return git_operations_module.push_repository(path, branch, force, set_upstream)

