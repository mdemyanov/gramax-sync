"""Тесты для определения статуса репозиториев."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gramax_sync.git.status import get_repository_status


def test_get_repository_status_not_found(tmp_path):
    """Тест статуса для несуществующего репозитория."""
    repo_path = tmp_path / "nonexistent"
    status = get_repository_status(repo_path)
    assert status == "not_found"


def test_get_repository_status_not_git_repo(tmp_path):
    """Тест статуса для директории, которая не является Git репозиторием."""
    repo_path = tmp_path / "not_git"
    repo_path.mkdir()
    status = get_repository_status(repo_path)
    assert status == "not_found"


@patch("gramax_sync.git.status.Repo")
def test_get_repository_status_clean(mock_repo_class, tmp_path):
    """Тест статуса для чистого репозитория."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = False
    mock_branch = MagicMock()
    mock_branch.name = "private"
    mock_repo.active_branch = mock_branch
    mock_repo.refs = {"origin/private": MagicMock()}
    mock_repo.iter_commits.return_value = []  # Нет коммитов
    mock_repo_class.return_value = mock_repo

    status = get_repository_status(repo_path)
    assert status == "clean"


@patch("gramax_sync.git.status.Repo")
def test_get_repository_status_modified(mock_repo_class, tmp_path):
    """Тест статуса для репозитория с незакоммиченными изменениями."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = True
    mock_repo_class.return_value = mock_repo

    status = get_repository_status(repo_path)
    assert status == "modified"


@patch("gramax_sync.git.status.Repo")
def test_get_repository_status_ahead(mock_repo_class, tmp_path):
    """Тест статуса для репозитория впереди remote."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = False
    mock_branch = MagicMock()
    mock_branch.name = "private"
    mock_repo.active_branch = mock_branch
    mock_repo.refs = {"origin/private": MagicMock()}
    # Нет коммитов в remote, но есть локальные
    mock_repo.iter_commits.side_effect = [
        [],  # origin/private..private (нет коммитов в remote)
        [MagicMock()],  # private..origin/private (есть локальные коммиты)
    ]
    mock_repo_class.return_value = mock_repo

    status = get_repository_status(repo_path)
    assert status == "ahead"


@patch("gramax_sync.git.status.Repo")
def test_get_repository_status_behind(mock_repo_class, tmp_path):
    """Тест статуса для репозитория отстающего от remote."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = False
    mock_branch = MagicMock()
    mock_branch.name = "private"
    mock_repo.active_branch = mock_branch
    mock_repo.refs = {"origin/private": MagicMock()}
    # Есть коммиты в remote, но нет локальных
    mock_repo.iter_commits.side_effect = [
        [MagicMock()],  # origin/private..private (есть коммиты в remote)
        [],  # private..origin/private (нет локальных коммитов)
    ]
    mock_repo_class.return_value = mock_repo

    status = get_repository_status(repo_path)
    assert status == "behind"


@patch("gramax_sync.git.status.Repo")
def test_get_repository_status_diverged(mock_repo_class, tmp_path):
    """Тест статуса для репозитория с разошедшимися ветками."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = False
    mock_branch = MagicMock()
    mock_branch.name = "private"
    mock_repo.active_branch = mock_branch
    mock_repo.refs = {"origin/private": MagicMock()}
    # Есть и локальные, и remote коммиты
    mock_repo.iter_commits.side_effect = [
        [MagicMock()],  # origin/private..private (есть коммиты в remote)
        [MagicMock()],  # private..origin/private (есть локальные коммиты)
    ]
    mock_repo_class.return_value = mock_repo

    status = get_repository_status(repo_path)
    assert status == "diverged"


@patch("gramax_sync.git.status.Repo")
def test_get_repository_status_error(mock_repo_class, tmp_path):
    """Тест статуса при ошибке."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo_class.side_effect = Exception("Unexpected error")
    
    status = get_repository_status(repo_path)
    assert status == "error"


@patch("gramax_sync.git.status.Repo")
def test_get_repository_status_no_remote_branch(mock_repo_class, tmp_path):
    """Тест статуса когда remote ветка не найдена."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = False
    mock_branch = MagicMock()
    mock_branch.name = "private"
    mock_repo.active_branch = mock_branch
    # Remote ветка не найдена (KeyError)
    mock_repo.refs = {}
    mock_repo.iter_commits.return_value = [MagicMock()]  # Есть локальные коммиты
    mock_repo_class.return_value = mock_repo
    
    status = get_repository_status(repo_path)
    assert status == "ahead"


@patch("gramax_sync.git.status.Repo")
def test_get_repository_status_no_remote_branch_no_commits(mock_repo_class, tmp_path):
    """Тест статуса когда remote ветка не найдена и нет коммитов."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = False
    mock_branch = MagicMock()
    mock_branch.name = "private"
    mock_repo.active_branch = mock_branch
    mock_repo.refs = {}
    mock_repo.iter_commits.return_value = []  # Нет коммитов
    mock_repo_class.return_value = mock_repo
    
    status = get_repository_status(repo_path)
    assert status == "clean"


@patch("gramax_sync.git.status.Repo")
def test_get_repository_status_no_remote(mock_repo_class, tmp_path):
    """Тест статуса когда remote не настроен."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = False
    mock_branch = MagicMock()
    mock_branch.name = "private"
    mock_repo.active_branch = mock_branch
    # Remote не настроен (ValueError)
    mock_repo.remote.side_effect = ValueError("Remote not found")
    mock_repo.iter_commits.return_value = [MagicMock()]  # Есть локальные коммиты
    mock_repo_class.return_value = mock_repo
    
    status = get_repository_status(repo_path)
    assert status == "ahead"


@patch("gramax_sync.git.status.Repo")
def test_get_repository_status_no_remote_no_commits(mock_repo_class, tmp_path):
    """Тест статуса когда remote не настроен и нет коммитов."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = False
    mock_branch = MagicMock()
    mock_branch.name = "private"
    mock_repo.active_branch = mock_branch
    mock_repo.remote.side_effect = ValueError("Remote not found")
    mock_repo.iter_commits.return_value = []  # Нет коммитов
    mock_repo_class.return_value = mock_repo
    
    status = get_repository_status(repo_path)
    assert status == "clean"


@patch("gramax_sync.git.status.Repo")
def test_get_repository_status_detached_head(mock_repo_class, tmp_path):
    """Тест статуса при detached HEAD."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    mock_repo = MagicMock()
    mock_repo.is_dirty.return_value = False
    # HEAD detached - при доступе к active_branch выбрасывается TypeError
    type(mock_repo).active_branch = property(lambda self: (_ for _ in ()).throw(TypeError("HEAD is detached")))
    mock_repo_class.return_value = mock_repo
    
    status = get_repository_status(repo_path)
    assert status == "error"


@patch("gramax_sync.git.status.Repo")
def test_get_repository_status_invalid_repo(mock_repo_class, tmp_path):
    """Тест статуса для невалидного репозитория."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    
    from git.exc import InvalidGitRepositoryError
    mock_repo_class.side_effect = InvalidGitRepositoryError("Invalid repo")
    
    status = get_repository_status(repo_path)
    assert status == "error"
