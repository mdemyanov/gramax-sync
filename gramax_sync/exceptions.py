"""Иерархия исключений для gramax-sync."""


class GramaxSyncError(Exception):
    """Базовое исключение для gramax-sync."""

    def __init__(self, message: str, context: dict | None = None):
        """Инициализировать исключение.

        Args:
            message: Сообщение об ошибке
            context: Дополнительный контекст ошибки (идентификаторы, параметры)
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}


class ConfigurationError(GramaxSyncError):
    """Ошибка конфигурации."""

    def __init__(
        self,
        message: str,
        config_path: str | None = None,
        context: dict | None = None,
    ):
        """Инициализировать ошибку конфигурации.

        Args:
            message: Сообщение об ошибке
            config_path: Путь к файлу конфигурации
            context: Дополнительный контекст ошибки
        """
        super().__init__(message, context)
        self.config_path = config_path


class GitOperationError(GramaxSyncError):
    """Ошибка Git операции."""

    def __init__(
        self,
        message: str,
        repository: str | None = None,
        operation: str | None = None,
        context: dict | None = None,
    ):
        """Инициализировать ошибку Git операции.

        Args:
            message: Сообщение об ошибке
            repository: Путь или имя репозитория
            operation: Название операции (clone, pull, push, commit)
            context: Дополнительный контекст ошибки
        """
        super().__init__(message, context)
        self.repository = repository
        self.operation = operation


class AuthenticationError(GramaxSyncError):
    """Ошибка аутентификации."""

    def __init__(
        self,
        message: str,
        service: str | None = None,
        context: dict | None = None,
    ):
        """Инициализировать ошибку аутентификации.

        Args:
            message: Сообщение об ошибке
            service: Название сервиса (GitLab, OAuth)
            context: Дополнительный контекст ошибки
        """
        super().__init__(message, context)
        self.service = service


class WorkspaceError(GramaxSyncError):
    """Ошибка работы с workspace."""

    def __init__(
        self,
        message: str,
        workspace_path: str | None = None,
        context: dict | None = None,
    ):
        """Инициализировать ошибку workspace.

        Args:
            message: Сообщение об ошибке
            workspace_path: Путь к workspace
            context: Дополнительный контекст ошибки
        """
        super().__init__(message, context)
        self.workspace_path = workspace_path


class ValidationError(GramaxSyncError):
    """Ошибка валидации данных."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: str | None = None,
        context: dict | None = None,
    ):
        """Инициализировать ошибку валидации.

        Args:
            message: Сообщение об ошибке
            field: Имя поля с ошибкой
            value: Значение поля
            context: Дополнительный контекст ошибки
        """
        super().__init__(message, context)
        self.field = field
        self.value = value

