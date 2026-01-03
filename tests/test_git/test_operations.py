"""Тесты для Git операций."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from git.exc import GitCommandError

from gramax_sync.git.operations import clone_repository, commit_repository, pull_repository, push_repository


@patch("gramax_sync.git.operations.Repo")
def test_clone_repository(mock_repo_class, tmp_path):
    """Тест клонирования репозитория."""
    mock_repo = MagicMock()
    mock_repo_class.clone_from.return_value = mock_repo

    repo_path = tmp_path / "test_repo"
    clone_repository("https://example.com/repo.git", repo_path, "private")

    mock_repo_class.clone_from.assert_called_once_with(
        "https://example.com/repo.git", str(repo_path), branch="private", depth=1
    )


@patch("gramax_sync.git.operations.Repo")
def test_clone_repository_branch_not_found(mock_repo_class, tmp_path):
    """Тест клонирования репозитория когда ветка не найдена."""
    # Первый вызов - ошибка из-за отсутствия ветки
    mock_repo_class.clone_from.side_effect = [
        GitCommandError("branch", "not found"),
        MagicMock(),  # Второй вызов - успешное клонирование
    ]

    repo_path = tmp_path / "test_repo"
    mock_repo = MagicMock()
    mock_repo.git.checkout.return_value = None
    mock_repo_class.clone_from.return_value = mock_repo

    clone_repository("https://example.com/repo.git", repo_path, "private")

    # Должно быть два вызова clone_from
    assert mock_repo_class.clone_from.call_count == 2


@patch("gramax_sync.git.operations.Repo")
def test_clone_repository_already_exists(mock_repo_class, tmp_path):
    """Тест что клонирование пропускается если репозиторий уже существует."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()  # Симулируем существующий репозиторий

    clone_repository("https://example.com/repo.git", repo_path, "private")

    # clone_from не должен вызываться
    mock_repo_class.clone_from.assert_not_called()


@patch("gramax_sync.git.operations.Repo")
def test_pull_repository(mock_repo_class, tmp_path):
    """Тест обновления репозитория."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = False
    mock_repo.active_branch.name = "private"
    mock_repo.remote.return_value = MagicMock()
    mock_repo_class.return_value = mock_repo

    pull_repository(repo_path, "private")

    mock_repo_class.assert_called_once_with(str(repo_path))
    mock_repo.remote.assert_called_once_with(name="origin")


@patch("gramax_sync.git.operations.Repo")
def test_pull_repository_with_changes(mock_repo_class, tmp_path):
    """Тест что pull пропускается если есть незакоммиченные изменения."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = True
    mock_repo_class.return_value = mock_repo

    pull_repository(repo_path, "private")

    # remote.pull не должен вызываться
    mock_repo.remote.assert_not_called()


def test_pull_repository_not_found(tmp_path):
    """Тест что pull выбрасывает ошибку если репозиторий не найден."""
    repo_path = tmp_path / "nonexistent"

    with pytest.raises(FileNotFoundError):
        pull_repository(repo_path, "private")


def test_pull_repository_not_git_repo(tmp_path):
    """Тест что pull выбрасывает ошибку если путь не является Git репозиторием."""
    repo_path = tmp_path / "not_git"
    repo_path.mkdir()

    from git.exc import InvalidGitRepositoryError

    with pytest.raises(InvalidGitRepositoryError):
        pull_repository(repo_path, "private")


@patch("gramax_sync.git.operations.Repo")
def test_commit_repository(mock_repo_class, tmp_path):
    """Тест коммита изменений в репозитории."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = True
    mock_repo.untracked_files = []
    mock_repo.git.add.return_value = None
    mock_index = MagicMock()
    mock_diff_item = MagicMock()
    mock_diff_item.b_path = "test.txt"
    mock_diff_item.change_type = "M"
    mock_index.diff.return_value = [mock_diff_item]
    mock_commit = MagicMock()
    mock_commit.hexsha = "abc1234"
    mock_index.commit.return_value = mock_commit
    mock_repo.index = mock_index
    mock_repo_class.return_value = mock_repo

    result = commit_repository(repo_path, "Test commit", add_all=True)

    assert result == "abc1234"
    mock_repo.git.add.assert_called_once_with(".")
    mock_index.commit.assert_called_once_with("Test commit")


@patch("gramax_sync.git.operations.Repo")
def test_commit_repository_auto_message(mock_repo_class, tmp_path):
    """Тест коммита с автогенерацией сообщения."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = True
    mock_repo.untracked_files = ["new_file.txt"]
    mock_repo.git.add.return_value = None
    mock_config = MagicMock()
    mock_config.get_value.return_value = "Test User"
    mock_repo.config_reader.return_value = mock_config
    mock_index = MagicMock()
    mock_diff_item = MagicMock()
    mock_diff_item.b_path = "modified.txt"
    mock_diff_item.change_type = "M"
    mock_index.diff.return_value = [mock_diff_item]
    mock_commit = MagicMock()
    mock_commit.hexsha = "def5678"
    mock_index.commit.return_value = mock_commit
    mock_repo.index = mock_index
    mock_repo_class.return_value = mock_repo

    result = commit_repository(repo_path, None, add_all=True)

    assert result == "def5678"
    # Проверяем, что сообщение было сгенерировано
    assert mock_index.commit.called
    call_args = mock_index.commit.call_args[0][0]
    assert "[gramax-sync]" in call_args
    assert "Test User" in call_args


@patch("gramax_sync.git.operations.Repo")
def test_commit_repository_no_changes(mock_repo_class, tmp_path):
    """Тест что commit возвращает None если нет изменений."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = False
    mock_repo.untracked_files = []
    mock_repo_class.return_value = mock_repo

    result = commit_repository(repo_path, "Test commit", add_all=True)

    assert result is None
    mock_repo.git.add.assert_not_called()


@patch("gramax_sync.git.operations.Repo")
def test_commit_repository_no_add(mock_repo_class, tmp_path):
    """Тест коммита с флагом add_all=False."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = True
    mock_repo.untracked_files = []
    mock_repo.git.add.return_value = None
    mock_index = MagicMock()
    mock_diff_item = MagicMock()
    mock_diff_item.b_path = "test.txt"
    mock_diff_item.change_type = "M"
    mock_index.diff.return_value = [mock_diff_item]
    mock_commit = MagicMock()
    mock_commit.hexsha = "xyz9876"
    mock_index.commit.return_value = mock_commit
    mock_repo.index = mock_index
    mock_repo_class.return_value = mock_repo

    result = commit_repository(repo_path, "Test commit", add_all=False)

    assert result == "xyz9876"
    mock_repo.git.add.assert_called_once_with("-u")


def test_commit_repository_not_found(tmp_path):
    """Тест что commit выбрасывает ошибку если репозиторий не найден."""
    repo_path = tmp_path / "nonexistent"

    with pytest.raises(FileNotFoundError):
        commit_repository(repo_path, "Test commit")


def test_commit_repository_not_git_repo(tmp_path):
    """Тест что commit выбрасывает ошибку если путь не является Git репозиторием."""
    repo_path = tmp_path / "not_git"
    repo_path.mkdir()

    from git.exc import InvalidGitRepositoryError

    with pytest.raises(InvalidGitRepositoryError):
        commit_repository(repo_path, "Test commit")


@patch("gramax_sync.git.operations.Repo")
def test_push_repository(mock_repo_class, tmp_path):
    """Тест успешной отправки изменений."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.active_branch.name = "private"
    mock_remote = MagicMock()
    mock_remote_branch = MagicMock()
    mock_repo.remote.return_value = mock_remote
    mock_repo.refs = {"origin/private": mock_remote_branch}
    
    # Мокируем unpushed commits
    mock_commits = [MagicMock(), MagicMock()]  # 2 коммита
    mock_repo.iter_commits.return_value = mock_commits
    mock_repo_class.return_value = mock_repo

    result = push_repository(repo_path, "private")

    assert result == 2
    mock_repo.remote.assert_called_once_with(name="origin")
    mock_remote.fetch.assert_called_once()
    mock_remote.push.assert_called_once_with("private")


@patch("gramax_sync.git.operations.Repo")
def test_push_repository_no_commits(mock_repo_class, tmp_path):
    """Тест push без unpushed commits."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.active_branch.name = "private"
    mock_remote = MagicMock()
    mock_remote_branch = MagicMock()
    mock_repo.remote.return_value = mock_remote
    mock_repo.refs = {"origin/private": mock_remote_branch}
    
    # Нет unpushed commits
    mock_repo.iter_commits.return_value = []
    mock_repo_class.return_value = mock_repo

    result = push_repository(repo_path, "private")

    assert result is None
    mock_remote.push.assert_not_called()


@patch("gramax_sync.git.operations.Repo")
def test_push_repository_force(mock_repo_class, tmp_path):
    """Тест force push."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.active_branch.name = "private"
    mock_remote = MagicMock()
    mock_remote_branch = MagicMock()
    mock_repo.remote.return_value = mock_remote
    mock_repo.refs = {"origin/private": mock_remote_branch}
    
    mock_commits = [MagicMock()]
    mock_repo.iter_commits.return_value = mock_commits
    mock_repo_class.return_value = mock_repo

    result = push_repository(repo_path, "private", force=True)

    assert result == 1
    mock_remote.push.assert_called_once_with("private", force=True)


@patch("gramax_sync.git.operations.Repo")
def test_push_repository_set_upstream(mock_repo_class, tmp_path):
    """Тест установки upstream."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.active_branch.name = "private"
    mock_remote = MagicMock()
    mock_repo.remote.return_value = mock_remote
    
    # Remote ветка не найдена - все коммиты считаются unpushed
    mock_commits = [MagicMock()]
    mock_repo.iter_commits.return_value = mock_commits
    # Симулируем отсутствие remote ветки
    mock_repo.refs = {}
    mock_repo_class.return_value = mock_repo

    result = push_repository(repo_path, "private", set_upstream=True)

    assert result == 1
    mock_remote.push.assert_called_once_with("private", set_upstream=True, force=False)


@patch("gramax_sync.git.operations.Repo")
def test_push_repository_rejected(mock_repo_class, tmp_path):
    """Тест обработки rejected push."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.active_branch.name = "private"
    mock_remote = MagicMock()
    mock_remote_branch = MagicMock()
    mock_repo.remote.return_value = mock_remote
    mock_repo.refs = {"origin/private": mock_remote_branch}
    
    mock_commits = [MagicMock()]
    mock_repo.iter_commits.return_value = mock_commits
    mock_repo_class.return_value = mock_repo
    
    # Симулируем rejected push
    mock_remote.push.side_effect = GitCommandError("push", "rejected: protected branch")

    with pytest.raises(GitCommandError) as exc_info:
        push_repository(repo_path, "private")
    
    assert "отклонён" in str(exc_info.value).lower() or "rejected" in str(exc_info.value).lower()


@patch("gramax_sync.git.operations.Repo")
def test_push_repository_network_error(mock_repo_class, tmp_path):
    """Тест обработки сетевой ошибки."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.active_branch.name = "private"
    mock_remote = MagicMock()
    mock_remote_branch = MagicMock()
    mock_repo.remote.return_value = mock_remote
    mock_repo.refs = {"origin/private": mock_remote_branch}
    
    mock_commits = [MagicMock()]
    mock_repo.iter_commits.return_value = mock_commits
    mock_repo_class.return_value = mock_repo
    
    # Симулируем сетевую ошибку
    mock_remote.push.side_effect = GitCommandError("push", "network error: connection refused")

    with pytest.raises(GitCommandError) as exc_info:
        push_repository(repo_path, "private")
    
    assert "сети" in str(exc_info.value).lower() or "network" in str(exc_info.value).lower()


def test_push_repository_not_found(tmp_path):
    """Тест что push выбрасывает ошибку если репозиторий не найден."""
    repo_path = tmp_path / "nonexistent"

    with pytest.raises(FileNotFoundError):
        push_repository(repo_path, "private")


def test_push_repository_not_git_repo(tmp_path):
    """Тест что push выбрасывает ошибку если путь не является Git репозиторием."""
    repo_path = tmp_path / "not_git"
    repo_path.mkdir()

    from git.exc import InvalidGitRepositoryError

    with pytest.raises(InvalidGitRepositoryError):
        push_repository(repo_path, "private")


@patch("gramax_sync.git.operations.Repo")
def test_push_repository_no_remote(mock_repo_class, tmp_path):
    """Тест что push выбрасывает ошибку если remote не настроен."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.active_branch.name = "private"
    mock_repo.remote.side_effect = ValueError("Remote 'origin' not found")
    mock_repo_class.return_value = mock_repo

    with pytest.raises(GitCommandError) as exc_info:
        push_repository(repo_path, "private")
    
    assert "remote" in str(exc_info.value).lower() or "origin" in str(exc_info.value).lower()


@patch("gramax_sync.git.operations.Repo")
def test_clone_repository_branch_not_found_create_branch(mock_repo_class, tmp_path):
    """Тест клонирования когда ветка не найдена и создается новая."""
    repo_path = tmp_path / "test_repo"
    
    # Создаем мок репозитория
    mock_repo = MagicMock()
    
    # Настраиваем checkout: первый вызов (без -b) выбрасывает ошибку,
    # второй вызов (с -b) успешен
    def checkout_side_effect(*args):
        if args and args[0] == "-b":
            return None  # Успешное создание ветки
        raise GitCommandError("branch", "not found")
    
    mock_repo.git.checkout.side_effect = checkout_side_effect
    
    # Первый вызов - ошибка из-за отсутствия ветки
    # Второй вызов - успешное клонирование без ветки
    mock_repo_class.clone_from.side_effect = [
        GitCommandError("branch", "not found"),
        mock_repo,  # Второй вызов возвращает мок репозитория
    ]
    
    clone_repository("https://example.com/repo.git", repo_path, "private")
    
    # Должен быть вызов checkout с -b для создания ветки
    # Первый вызов: checkout("private") - ошибка
    # Второй вызов: checkout("-b", "private") - успех
    assert mock_repo.git.checkout.call_count == 2


@patch("gramax_sync.git.operations.Repo")
def test_pull_repository_switch_branch(mock_repo_class, tmp_path):
    """Тест pull когда нужно переключиться на другую ветку."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = False
    mock_branch = MagicMock()
    mock_branch.name = "main"  # Текущая ветка
    mock_repo.active_branch = mock_branch
    mock_repo.git.checkout.return_value = None
    mock_remote = MagicMock()
    mock_repo.remote.return_value = mock_remote
    mock_repo_class.return_value = mock_repo
    
    pull_repository(repo_path, "private")
    
    # Должен быть вызов checkout для переключения на private
    mock_repo.git.checkout.assert_called_once_with("private")


@patch("gramax_sync.git.operations.Repo")
def test_pull_repository_create_branch_from_remote(mock_repo_class, tmp_path):
    """Тест pull когда ветка не существует локально и создается из remote."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = False
    mock_branch = MagicMock()
    mock_branch.name = "main"
    mock_repo.active_branch = mock_branch
    # Первый checkout - ошибка (ветка не существует)
    # Второй checkout - создание из remote
    mock_repo.git.checkout.side_effect = [
        GitCommandError("branch", "not found"),
        None,  # Успешное создание из remote
    ]
    mock_remote = MagicMock()
    mock_repo.remote.return_value = mock_remote
    mock_repo_class.return_value = mock_repo
    
    pull_repository(repo_path, "private")
    
    # Должен быть вызов checkout с -b и origin/private
    assert mock_repo.git.checkout.call_count >= 1


@patch("gramax_sync.git.operations.Repo")
def test_pull_repository_create_new_branch(mock_repo_class, tmp_path):
    """Тест pull когда ветка не существует ни локально, ни в remote."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = False
    mock_branch = MagicMock()
    mock_branch.name = "main"
    mock_repo.active_branch = mock_branch
    # Оба checkout - ошибки, создаем новую ветку
    mock_repo.git.checkout.side_effect = [
        GitCommandError("branch", "not found"),
        GitCommandError("remote", "not found"),
        None,  # Успешное создание новой ветки
    ]
    mock_remote = MagicMock()
    mock_repo.remote.return_value = mock_remote
    mock_repo_class.return_value = mock_repo
    
    pull_repository(repo_path, "private")
    
    # Должен быть вызов checkout с -b для создания новой ветки
    assert mock_repo.git.checkout.call_count >= 2


@patch("gramax_sync.git.operations.Repo")
def test_pull_repository_merge_conflict(mock_repo_class, tmp_path):
    """Тест pull когда есть конфликты при слиянии."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = False
    mock_branch = MagicMock()
    mock_branch.name = "private"
    mock_repo.active_branch = mock_branch
    mock_remote = MagicMock()
    mock_remote.pull.side_effect = GitCommandError("merge", "conflict detected")
    mock_repo.remote.return_value = mock_remote
    mock_repo_class.return_value = mock_repo
    
    with pytest.raises(GitCommandError, match="конфликты"):
        pull_repository(repo_path, "private")


@patch("gramax_sync.git.operations.getpass")
@patch("gramax_sync.git.operations.Repo")
def test_generate_commit_message_with_exception(mock_repo_class, mock_getpass, tmp_path):
    """Тест генерации сообщения коммита когда config_reader выбрасывает исключение."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_config = MagicMock()
    mock_config.get_value.side_effect = Exception("Config error")
    mock_repo.config_reader.return_value = mock_config
    mock_repo.index.diff.return_value = []
    mock_repo.untracked_files = []
    mock_getpass.getuser.return_value = "testuser"
    mock_repo_class.return_value = mock_repo
    
    from gramax_sync.git.operations import _generate_commit_message
    
    message = _generate_commit_message(mock_repo)
    assert "testuser" in message
    assert "[gramax-sync]" in message


@patch("gramax_sync.git.operations.getpass")
@patch("gramax_sync.git.operations.Repo")
def test_generate_commit_message_with_deleted_files(mock_repo_class, mock_getpass, tmp_path):
    """Тест генерации сообщения коммита с удаленными файлами."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_config = MagicMock()
    mock_config.get_value.return_value = "testuser"
    mock_repo.config_reader.return_value = mock_config
    
    # Мокируем diff с удаленными файлами
    mock_diff_item = MagicMock()
    mock_diff_item.change_type = "D"
    mock_diff_item.b_path = "deleted_file.txt"
    mock_repo.index.diff.return_value = [mock_diff_item]
    mock_repo.untracked_files = []
    mock_repo_class.return_value = mock_repo
    
    from gramax_sync.git.operations import _generate_commit_message
    
    message = _generate_commit_message(mock_repo)
    assert "Deleted files" in message
    assert "deleted_file.txt" in message


@patch("gramax_sync.git.operations.Repo")
def test_commit_repository_first_commit(mock_repo_class, tmp_path):
    """Тест коммита для первого коммита (HEAD не существует)."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = True
    mock_repo.untracked_files = ["new_file.txt"]
    
    # HEAD не существует - первый коммит
    # Первый вызов diff("HEAD") выбрасывает исключение
    # Второй вызов diff(None) возвращает изменения
    mock_diff_item = MagicMock()
    mock_diff_item.change_type = "A"
    mock_diff_item.b_path = "new_file.txt"
    
    def diff_side_effect(*args):
        if args and args[0] == "HEAD":
            raise ValueError("HEAD not found")
        return [mock_diff_item]
    
    mock_repo.index.diff.side_effect = diff_side_effect
    
    # Мокируем iter_blobs для проверки индекса (вызывается в блоке except)
    mock_blob = MagicMock()
    mock_repo.index.iter_blobs.return_value = [(mock_blob, "new_file.txt")]
    
    mock_commit = MagicMock()
    mock_commit.hexsha = "abc123"
    mock_repo.index.commit.return_value = mock_commit
    mock_repo_class.return_value = mock_repo
    
    result = commit_repository(repo_path, add_all=True)
    
    assert result == "abc123"
    mock_repo.git.add.assert_called_once_with(".")


@patch("gramax_sync.git.operations.Repo")
def test_commit_repository_no_changes_after_add(mock_repo_class, tmp_path):
    """Тест коммита когда после add нет изменений."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = False
    mock_repo.untracked_files = []
    mock_repo.index.diff.return_value = []
    mock_repo.index.iter_blobs.return_value = []
    mock_repo_class.return_value = mock_repo
    
    result = commit_repository(repo_path, add_all=True)
    
    assert result is None


@patch("gramax_sync.git.operations.Repo")
def test_push_repository_branch_not_found(mock_repo_class, tmp_path):
    """Тест push когда ветка не найдена."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_branch = MagicMock()
    mock_branch.name = "main"
    mock_repo.active_branch = mock_branch
    mock_repo.git.checkout.side_effect = GitCommandError("branch", "not found")
    mock_remote = MagicMock()
    mock_repo.remote.return_value = mock_remote
    mock_repo_class.return_value = mock_repo
    
    with pytest.raises(GitCommandError, match="не найдена"):
        push_repository(repo_path, "private")


@patch("gramax_sync.git.operations.Repo")
def test_push_repository_no_remote_branch(mock_repo_class, tmp_path):
    """Тест push когда remote ветка не найдена."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_branch = MagicMock()
    mock_branch.name = "private"
    mock_repo.active_branch = mock_branch
    mock_remote = MagicMock()
    mock_remote.fetch.return_value = None
    # Remote ветка не найдена
    mock_repo.refs = {}
    mock_repo.iter_commits.return_value = [MagicMock(), MagicMock()]  # Есть локальные коммиты
    mock_repo.remote.return_value = mock_remote
    mock_repo_class.return_value = mock_repo
    
    result = push_repository(repo_path, "private")
    
    # Должен вернуть количество коммитов
    assert result == 2


@patch("gramax_sync.git.operations.Repo")
def test_push_repository_remote_unavailable(mock_repo_class, tmp_path):
    """Тест push когда remote недоступен."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_branch = MagicMock()
    mock_branch.name = "private"
    mock_repo.active_branch = mock_branch
    mock_remote = MagicMock()
    mock_remote.fetch.side_effect = ValueError("Remote unavailable")
    mock_repo.iter_commits.return_value = [MagicMock()]  # Есть локальные коммиты
    mock_repo.remote.return_value = mock_remote
    mock_repo_class.return_value = mock_repo
    
    result = push_repository(repo_path, "private")
    
    # Должен вернуть количество коммитов даже если remote недоступен
    assert result == 1


@patch("gramax_sync.git.operations.Repo")
def test_push_repository_rejected(mock_repo_class, tmp_path):
    """Тест push когда push отклонен."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_branch = MagicMock()
    mock_branch.name = "private"
    mock_repo.active_branch = mock_branch
    mock_remote = MagicMock()
    mock_remote.fetch.return_value = None
    mock_remote_branch = MagicMock()
    mock_repo.refs = {"origin/private": mock_remote_branch}
    mock_repo.iter_commits.return_value = [MagicMock()]
    mock_remote.push.side_effect = GitCommandError("push", "rejected: protected branch")
    mock_repo.remote.return_value = mock_remote
    mock_repo_class.return_value = mock_repo
    
    with pytest.raises(GitCommandError, match="отклонён"):
        push_repository(repo_path, "private")


@patch("gramax_sync.git.operations.Repo")
def test_push_repository_network_error(mock_repo_class, tmp_path):
    """Тест push при сетевой ошибке."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_branch = MagicMock()
    mock_branch.name = "private"
    mock_repo.active_branch = mock_branch
    mock_remote = MagicMock()
    mock_remote.fetch.return_value = None
    mock_remote_branch = MagicMock()
    mock_repo.refs = {"origin/private": mock_remote_branch}
    mock_repo.iter_commits.return_value = [MagicMock()]
    mock_remote.push.side_effect = GitCommandError("push", "network connection error")
    mock_repo.remote.return_value = mock_remote
    mock_repo_class.return_value = mock_repo
    
    with pytest.raises(GitCommandError, match="сети"):
        push_repository(repo_path, "private")


@patch("gramax_sync.git.operations.Repo")
def test_push_repository_unexpected_error(mock_repo_class, tmp_path):
    """Тест push при неожиданной ошибке."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_branch = MagicMock()
    mock_branch.name = "private"
    mock_repo.active_branch = mock_branch
    mock_repo.remote.side_effect = Exception("Unexpected error")
    mock_repo_class.return_value = mock_repo
    
    with pytest.raises(GitCommandError, match="Неожиданная ошибка"):
        push_repository(repo_path, "private")
