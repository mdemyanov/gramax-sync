"""Git операции: clone, pull, push, commit."""

import getpass
from datetime import datetime
from pathlib import Path

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError


def clone_repository(url: str, path: Path, branch: str = "private") -> None:
    """Клонировать репозиторий.

    Клонирует репозиторий по указанному URL в указанную директорию
    и переключается на указанную ветку.

    Args:
        url: URL репозитория для клонирования
        path: Путь к директории, куда клонировать
        branch: Ветка для переключения после клонирования (по умолчанию "private")

    Raises:
        GitCommandError: Если клонирование не удалось
        OSError: Если не удалось создать директорию
    """
    # Проверяем, существует ли уже репозиторий
    if path.exists() and (path / ".git").exists():
        # Репозиторий уже существует, пропускаем
        return

    # Создаём родительскую директорию
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Клонируем репозиторий
        repo = Repo.clone_from(url, str(path), branch=branch, depth=1)
    except GitCommandError as e:
        # Если ветка не найдена, пробуем клонировать master/main и создать ветку
        if "not found" in str(e).lower() or "couldn't find remote ref" in str(e).lower():
            try:
                # Пробуем клонировать без указания ветки
                repo = Repo.clone_from(url, str(path), depth=1)
                # Пробуем переключиться на нужную ветку или создать её
                try:
                    repo.git.checkout(branch)
                except GitCommandError:
                    # Ветка не существует, создаём её
                    repo.git.checkout("-b", branch)
            except GitCommandError as e2:
                raise GitCommandError(f"Не удалось клонировать репозиторий {url}: {e2}") from e2
        else:
            raise


def pull_repository(path: Path, branch: str = "private") -> None:
    """Обновить репозиторий.

    Выполняет git pull для указанного репозитория на указанной ветке.

    Args:
        path: Путь к репозиторию
        branch: Ветка для обновления (по умолчанию "private")

    Raises:
        InvalidGitRepositoryError: Если путь не является Git репозиторием
        GitCommandError: Если pull не удался (например, конфликты)
        FileNotFoundError: Если репозиторий не существует
    """
    if not path.exists():
        raise FileNotFoundError(f"Репозиторий не найден: {path}")

    if not (path / ".git").exists():
        raise InvalidGitRepositoryError(f"Путь не является Git репозиторием: {path}")

    try:
        repo = Repo(str(path))

        # Проверяем, есть ли изменения в рабочей директории
        if repo.is_dirty():
            # Есть незакоммиченные изменения, пропускаем pull
            return

        # Переключаемся на нужную ветку, если не на ней
        if repo.active_branch.name != branch:
            try:
                repo.git.checkout(branch)
            except GitCommandError:
                # Ветка не существует локально, пробуем создать из remote
                try:
                    repo.git.checkout("-b", branch, f"origin/{branch}")
                except GitCommandError:
                    # Remote ветки тоже нет, создаём новую
                    repo.git.checkout("-b", branch)

        # Выполняем pull
        origin = repo.remote(name="origin")
        origin.pull(branch)
    except GitCommandError as e:
        # Обрабатываем конфликты и другие ошибки
        if "merge conflict" in str(e).lower() or "conflict" in str(e).lower():
            raise GitCommandError(f"Обнаружены конфликты при обновлении {path}: {e}") from e
        raise


def _generate_commit_message(repo: Repo) -> str:
    """Сгенерировать сообщение коммита на основе изменений.

    Args:
        repo: Git репозиторий

    Returns:
        Сгенерированное сообщение коммита
    """
    # Получаем имя пользователя из git config или системное
    try:
        username = repo.config_reader().get_value("user", "name", default=None)
        if not username:
            username = getpass.getuser()
    except Exception:
        username = getpass.getuser()

    # Получаем текущую дату/время в ISO формате
    timestamp = datetime.now().isoformat()

    # Получаем список изменённых файлов
    modified_files = []
    added_files = []
    deleted_files = []

    # Получаем статус файлов в staging area (после git add)
    # Используем diff между HEAD и индексом
    try:
        for item in repo.index.diff("HEAD"):  # Изменения в staging area
            if item.change_type == "A":
                added_files.append(item.b_path)
            elif item.change_type == "D":
                deleted_files.append(item.b_path)
            else:
                modified_files.append(item.b_path)
    except (ValueError, KeyError):
        # HEAD не существует (первый коммит), используем diff с None
        for item in repo.index.diff(None):
            if item.change_type == "A":
                added_files.append(item.b_path)
            elif item.change_type == "D":
                deleted_files.append(item.b_path)
            else:
                modified_files.append(item.b_path)

    # Также проверяем неотслеживаемые файлы, которые были добавлены
    # После git add они уже в staging area, но проверим на всякий случай
    untracked = repo.untracked_files
    added_files.extend(untracked)

    # Формируем сообщение
    message_parts = [f"[gramax-sync] Update by {username} at {timestamp}"]

    if modified_files:
        message_parts.append("\nModified files:")
        for file in sorted(modified_files):
            message_parts.append(f"- {file}")

    if added_files:
        message_parts.append("\nAdded files:")
        for file in sorted(added_files):
            message_parts.append(f"- {file}")

    if deleted_files:
        message_parts.append("\nDeleted files:")
        for file in sorted(deleted_files):
            message_parts.append(f"- {file}")

    return "\n".join(message_parts)


def commit_repository(
    path: Path,
    message: str | None = None,
    add_all: bool = True,
) -> str | None:
    """Закоммитить изменения в репозитории.

    Выполняет git commit для указанного репозитория. Если сообщение
    не указано, генерирует его автоматически на основе изменений.

    Args:
        path: Путь к репозиторию
        message: Сообщение коммита (если None, генерируется автоматически)
        add_all: Добавлять ли все файлы перед коммитом (по умолчанию True)

    Returns:
        Хеш коммита или None если нет изменений для коммита

    Raises:
        InvalidGitRepositoryError: Если путь не является Git репозиторием
        GitCommandError: Если commit не удался
        FileNotFoundError: Если репозиторий не существует
    """
    if not path.exists():
        raise FileNotFoundError(f"Репозиторий не найден: {path}")

    if not (path / ".git").exists():
        raise InvalidGitRepositoryError(f"Путь не является Git репозиторием: {path}")

    try:
        repo = Repo(str(path))

        # Проверяем, есть ли изменения перед добавлением
        is_dirty = repo.is_dirty()
        has_untracked = bool(repo.untracked_files)

        if not is_dirty and not has_untracked:
            # Нет изменений для коммита
            return None

        # Добавляем файлы в staging area
        if add_all:
            # Добавляем все файлы
            repo.git.add(".")
        else:
            # Добавляем только уже отслеживаемые изменённые файлы
            repo.git.add("-u")

        # Проверяем, есть ли что-то в staging area после добавления
        # Используем diff между HEAD и индексом
        has_staged_changes = False
        try:
            # Проверяем разницу между HEAD и индексом
            staged_diff = list(repo.index.diff("HEAD"))
            has_staged_changes = bool(staged_diff)
        except (ValueError, KeyError):
            # HEAD не существует (первый коммит) или другая проблема
            # Проверяем, есть ли файлы в индексе
            try:
                # Если есть файлы в индексе, значит есть что коммитить
                has_staged_changes = bool(list(repo.index.iter_blobs()))
            except Exception:
                # Если не удалось проверить, предполагаем что есть изменения
                has_staged_changes = True

        # Также проверяем неотслеживаемые файлы, которые были добавлены
        if not has_staged_changes and not repo.untracked_files:
            return None

        # Генерируем сообщение, если не указано
        if message is None:
            message = _generate_commit_message(repo)

        # Создаём коммит
        commit = repo.index.commit(message)

        return commit.hexsha
    except GitCommandError as e:
        raise GitCommandError(f"Не удалось создать коммит в {path}: {e}") from e


def push_repository(
    path: Path,
    branch: str = "private",
    force: bool = False,
    set_upstream: bool = False,
) -> int | None:
    """Отправить изменения в remote.
    
    Args:
        path: Путь к репозиторию
        branch: Ветка для отправки (по умолчанию "private")
        force: Использовать force push
        set_upstream: Установить upstream для новой ветки
    
    Returns:
        Количество отправленных коммитов или None если нечего отправлять
    
    Raises:
        InvalidGitRepositoryError: Если путь не является Git репозиторием
        GitCommandError: Если push не удался
        FileNotFoundError: Если репозиторий не существует
    """
    if not path.exists():
        raise FileNotFoundError(f"Репозиторий не найден: {path}")

    if not (path / ".git").exists():
        raise InvalidGitRepositoryError(f"Путь не является Git репозиторием: {path}")

    try:
        repo = Repo(str(path))

        # Проверяем наличие remote (origin)
        try:
            remote = repo.remote(name="origin")
        except ValueError:
            raise GitCommandError(f"Remote 'origin' не настроен для репозитория {path}")

        # Переключаемся на нужную ветку, если не на ней
        if repo.active_branch.name != branch:
            try:
                repo.git.checkout(branch)
            except GitCommandError:
                raise GitCommandError(f"Ветка '{branch}' не найдена в репозитории {path}")

        # Проверяем наличие unpushed commits
        unpushed_count = 0
        try:
            # Пробуем получить remote ветку
            remote.fetch()
            try:
                remote_branch = repo.refs[f"origin/{branch}"]
                # Коммиты локально, которых нет в remote (мы впереди)
                commits_local = list(repo.iter_commits(f"origin/{branch}..{branch}"))
                unpushed_count = len(commits_local)
            except (KeyError, IndexError):
                # Remote ветка не найдена - все локальные коммиты считаются unpushed
                commits_local = list(repo.iter_commits(branch))
                unpushed_count = len(commits_local)
        except (ValueError, AttributeError):
            # Remote недоступен или другая проблема
            # Проверяем, есть ли вообще коммиты в ветке
            commits_local = list(repo.iter_commits(branch))
            unpushed_count = len(commits_local)

        # Если нет unpushed commits, возвращаем None
        if unpushed_count == 0:
            return None

        # Выполняем push
        try:
            if set_upstream:
                # Устанавливаем upstream и отправляем
                remote.push(branch, set_upstream=True, force=force)
            else:
                # Обычный push
                if force:
                    remote.push(branch, force=True)
                else:
                    remote.push(branch)
        except GitCommandError as e:
            error_msg = str(e).lower()
            if "rejected" in error_msg or "protected" in error_msg:
                raise GitCommandError(
                    f"Push отклонён для {path}: ветка защищена или нет прав. "
                    f"Используйте --force для принудительной отправки (осторожно!)."
                ) from e
            elif "network" in error_msg or "connection" in error_msg or "unreachable" in error_msg:
                raise GitCommandError(
                    f"Ошибка сети при отправке {path}: {e}"
                ) from e
            else:
                raise GitCommandError(f"Не удалось отправить изменения в {path}: {e}") from e

        return unpushed_count
    except GitCommandError:
        raise
    except Exception as e:
        raise GitCommandError(f"Неожиданная ошибка при отправке {path}: {e}") from e
