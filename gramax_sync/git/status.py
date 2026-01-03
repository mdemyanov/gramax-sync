"""Определение статуса Git репозиториев."""

from pathlib import Path

from git import Repo
from git.exc import InvalidGitRepositoryError


def get_repository_status(path: Path) -> str:
    """Получить статус репозитория.

    Определяет статус Git репозитория и возвращает одно из значений:
    - "clean" — репозиторий чистый, нет изменений
    - "modified" — есть незакоммиченные изменения
    - "ahead" — есть локальные коммиты, не отправленные в remote
    - "behind" — есть коммиты в remote, которых нет локально
    - "diverged" — ветки разошлись (есть и локальные, и remote коммиты)
    - "error" — ошибка при определении статуса
    - "not_found" — репозиторий не найден

    Args:
        path: Путь к репозиторию

    Returns:
        Строка со статусом репозитория
    """
    if not path.exists():
        return "not_found"

    if not (path / ".git").exists():
        return "not_found"

    try:
        repo = Repo(str(path))

        # Проверяем наличие изменений в рабочей директории
        if repo.is_dirty():
            return "modified"

        # Получаем информацию о ветке
        try:
            active_branch = repo.active_branch
            branch_name = active_branch.name

            # Получаем информацию о remote
            try:
                remote = repo.remote(name="origin")
                remote.fetch()

                # Сравниваем локальную и remote ветки
                try:
                    remote_branch = repo.refs[f"origin/{branch_name}"]
                    # Коммиты в remote, которых нет локально (мы отстаём)
                    commits_in_remote = list(repo.iter_commits(f"{branch_name}..origin/{branch_name}"))
                    # Коммиты локально, которых нет в remote (мы впереди)
                    commits_local = list(repo.iter_commits(f"origin/{branch_name}..{branch_name}"))

                    if commits_in_remote and commits_local:
                        return "diverged"
                    elif commits_in_remote:
                        return "behind"
                    elif commits_local:
                        return "ahead"
                    else:
                        return "clean"
                except (KeyError, IndexError):
                    # Remote ветка не найдена
                    if list(repo.iter_commits(branch_name)):
                        return "ahead"
                    else:
                        return "clean"
            except (ValueError, AttributeError):
                # Remote не настроен или недоступен
                if list(repo.iter_commits(branch_name)):
                    return "ahead"
                else:
                    return "clean"
        except (TypeError, AttributeError):
            # HEAD detached или другая проблема
            return "error"

    except InvalidGitRepositoryError:
        return "error"
    except Exception:
        return "error"
