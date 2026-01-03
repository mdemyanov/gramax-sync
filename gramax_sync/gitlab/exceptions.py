"""Исключения для модуля GitLab."""


class GitLabError(Exception):
    """Базовое исключение для ошибок GitLab."""

    pass


class GitLabAuthError(GitLabError):
    """Ошибка аутентификации в GitLab."""

    pass


class GitLabPermissionError(GitLabError):
    """Ошибка доступа к ресурсу GitLab."""

    pass


class GitLabNotFoundError(GitLabError):
    """Ресурс не найден в GitLab."""

    pass

