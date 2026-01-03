"""Модуль для работы с GitLab API."""

from gramax_sync.gitlab.client import GitLabClient
from gramax_sync.gitlab.exceptions import (
    GitLabAuthError,
    GitLabError,
    GitLabNotFoundError,
    GitLabPermissionError,
)

__all__ = [
    "GitLabClient",
    "GitLabError",
    "GitLabAuthError",
    "GitLabPermissionError",
    "GitLabNotFoundError",
]

