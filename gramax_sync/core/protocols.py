"""Протоколы для зависимостей (интерфейсы для Dependency Injection)."""

from pathlib import Path
from typing import Protocol

from gramax_sync.config.local_config import LocalConfig
from gramax_sync.config.models import Workspace


class ConfigManagerProtocol(Protocol):
    """Протокол для менеджера конфигурации."""

    def require_config(self) -> LocalConfig:
        """Загрузить конфигурацию или выбросить исключение.

        Returns:
            Объект LocalConfig

        Raises:
            FileNotFoundError: Если конфигурация не найдена
        """
        ...

    def load_config(self) -> LocalConfig | None:
        """Загрузить локальную конфигурацию из файла.

        Returns:
            Объект LocalConfig или None если файл не найден
        """
        ...

    def save_config(self, config: LocalConfig) -> None:
        """Сохранить локальную конфигурацию в файл.

        Args:
            config: Объект LocalConfig для сохранения
        """
        ...


class WorkspaceManagerProtocol(Protocol):
    """Протокол для менеджера workspace."""

    def list_repositories(self, workspace: Workspace) -> list[tuple[str, str, Path]]:
        """Получить список всех репозиториев.

        Args:
            workspace: Объект Workspace с конфигурацией

        Returns:
            Список кортежей (section_name, catalog_name, path) для каждого репозитория
        """
        ...

    def ensure_workspace_structure(self, workspace: Workspace) -> None:
        """Создать структуру директорий workspace.

        Создаёт структуру директорий {workspace_dir}/{section}/{catalog}/ для всех
        секций и каталогов в конфигурации.

        Args:
            workspace: Объект Workspace с конфигурацией

        Raises:
            OSError: Если не удалось создать директории
        """
        ...


class GitOperationsProtocol(Protocol):
    """Протокол для Git операций."""

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
        ...

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
        ...

    def get_repository_status(self, path: Path) -> str:
        """Получить статус репозитория.

        Args:
            path: Путь к репозиторию

        Returns:
            Статус репозитория (clean, modified, ahead, behind, diverged, error, not_found)

        Raises:
            FileNotFoundError: Если репозиторий не существует
        """
        ...

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
        ...

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
        ...

