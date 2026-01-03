"""Тесты для MCP инструментов."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gramax_sync.config.local_config import LocalConfig


def get_wrapped_function(func):
    """Получить оригинальную функцию из декорированной."""
    if hasattr(func, '__wrapped__'):
        return func.__wrapped__
    elif hasattr(func, 'fn'):
        return func.fn
    else:
        return func


@pytest.fixture
def mock_config():
    """Фикстура для мокирования конфигурации."""
    return LocalConfig(
        repo_url="https://gitlab.example.com/config-repo",
        workspace_dir="/tmp/test_workspace",
        base_url="https://gitlab.example.com",
        catalog_branch="private",
        sections=[
            {
                "name": "section1",
                "catalogs": [
                    {
                        "name": "catalog1",
                        "source": {"url": "https://gitlab.example.com"},
                    }
                ],
            }
        ],
    )


@pytest.fixture
def mock_repositories():
    """Фикстура для мокирования списка репозиториев."""
    return [
        ("section1", "catalog1", Path("/tmp/test_workspace/section1/catalog1")),
    ]


# Тестируем функции напрямую, обходя декоратор @mcp.tool()
@patch("gramax_sync.mcp.tools.workspace_list_repositories")
@patch("gramax_sync.mcp.tools.require_mcp_config")
def test_list_repositories_success(mock_require_config, mock_workspace_list, mock_config, mock_repositories):
    """Проверка успешного получения списка репозиториев."""
    mock_require_config.return_value = mock_config
    mock_workspace_list.return_value = mock_repositories
    
    from gramax_sync.mcp.tools import list_repositories as list_repos_func
    
    func = get_wrapped_function(list_repos_func)
    
    result = func()
    
    assert "📦 Список репозиториев" in result
    assert "section1" in result
    assert "catalog1" in result
    assert "Всего: 1 репозиториев" in result


@patch("gramax_sync.mcp.tools.require_mcp_config")
def test_list_repositories_no_config(mock_require_config):
    """Проверка обработки отсутствия конфигурации."""
    mock_require_config.side_effect = FileNotFoundError("Конфигурация не найдена")
    
    from gramax_sync.mcp.tools import list_repositories as list_repos_func
    
    func = get_wrapped_function(list_repos_func)
    
    result = func()
    
    assert "❌ Ошибка" in result
    assert "Конфигурация не найдена" in result


@patch("gramax_sync.mcp.tools.workspace_list_repositories")
@patch("gramax_sync.mcp.tools.require_mcp_config")
def test_list_repositories_filter(mock_require_config, mock_workspace_list, mock_config, mock_repositories):
    """Проверка фильтрации по секции."""
    mock_require_config.return_value = mock_config
    mock_workspace_list.return_value = mock_repositories
    
    from gramax_sync.mcp.tools import list_repositories as list_repos_func
    
    func = get_wrapped_function(list_repos_func)
    
    result = func(section="section1")
    
    assert "section1" in result


@patch("gramax_sync.mcp.tools.workspace_list_repositories")
@patch("gramax_sync.mcp.tools.require_mcp_config")
def test_list_repositories_empty(mock_require_config, mock_workspace_list, mock_config):
    """Проверка обработки пустого списка репозиториев."""
    mock_require_config.return_value = mock_config
    mock_workspace_list.return_value = []
    
    from gramax_sync.mcp.tools import list_repositories as list_repos_func
    
    func = get_wrapped_function(list_repos_func)
    
    result = func()
    
    assert "⚠️  Нет репозиториев" in result


@patch("gramax_sync.mcp.tools.get_git_status")
@patch("gramax_sync.mcp.tools.workspace_list_repositories")
@patch("gramax_sync.mcp.tools.require_mcp_config")
def test_get_repository_status_success(mock_require_config, mock_workspace_list, mock_get_status, mock_config, mock_repositories):
    """Проверка успешного получения статуса репозиториев."""
    mock_require_config.return_value = mock_config
    mock_workspace_list.return_value = mock_repositories
    mock_get_status.return_value = "clean"
    
    from gramax_sync.mcp.tools import get_repository_status as get_status_func
    
    func = get_wrapped_function(get_status_func)
    
    result = func()
    
    assert "📊 Статус репозиториев" in result
    assert "section1" in result
    assert "catalog1" in result
    assert "📈 Статистика" in result


@patch("gramax_sync.mcp.tools.get_git_status")
@patch("gramax_sync.mcp.tools.workspace_list_repositories")
@patch("gramax_sync.mcp.tools.require_mcp_config")
def test_get_repository_status_with_filters(mock_require_config, mock_workspace_list, mock_get_status, mock_config, mock_repositories):
    """Проверка фильтрации статуса по секции и каталогу."""
    mock_require_config.return_value = mock_config
    mock_workspace_list.return_value = mock_repositories
    mock_get_status.return_value = "modified"
    
    from gramax_sync.mcp.tools import get_repository_status as get_status_func
    
    func = get_wrapped_function(get_status_func)
    
    result = func(section="section1", catalog="catalog1")
    
    assert "📊 Статус репозиториев" in result


@patch("gramax_sync.mcp.tools.require_mcp_config")
def test_get_repository_status_no_config(mock_require_config):
    """Проверка обработки отсутствия конфигурации."""
    mock_require_config.side_effect = FileNotFoundError("Конфигурация не найдена")
    
    from gramax_sync.mcp.tools import get_repository_status as get_status_func
    
    func = get_wrapped_function(get_status_func)
    
    result = func()
    
    assert "❌ Ошибка" in result


def test_clone_repositories_success(mock_config, mock_repositories):
    """Проверка успешного клонирования репозиториев."""
    # Мокируем Path объекты
    mock_repo_path = MagicMock(spec=Path)
    mock_repo_path.exists.return_value = False
    mock_git_path = MagicMock(spec=Path)
    mock_git_path.exists.return_value = False
    mock_repo_path.__truediv__.return_value = mock_git_path
    
    mock_repos = [("section1", "catalog1", mock_repo_path)]
    
    with patch("gramax_sync.mcp.tools.require_mcp_config", return_value=mock_config):
        with patch("gramax_sync.mcp.tools.workspace_list_repositories", return_value=mock_repos):
            with patch("gramax_sync.mcp.tools.ensure_workspace_structure"):
                with patch("gramax_sync.mcp.tools.clone_repository"):
                    from gramax_sync.mcp.tools import clone_repositories as clone_func
                    
                    func = get_wrapped_function(clone_func)
                    
                    result = func()
                    
                    assert "📦 Клонирование репозиториев" in result
                    assert "✅" in result
                    assert "📊 Итоги" in result


def test_clone_repositories_already_exists(mock_config, mock_repositories):
    """Проверка пропуска уже существующих репозиториев."""
    # Мокируем Path объекты - репозиторий уже существует
    mock_repo_path = MagicMock(spec=Path)
    mock_repo_path.exists.return_value = True
    mock_git_path = MagicMock(spec=Path)
    mock_git_path.exists.return_value = True
    mock_repo_path.__truediv__.return_value = mock_git_path
    
    mock_repos = [("section1", "catalog1", mock_repo_path)]
    
    with patch("gramax_sync.mcp.tools.require_mcp_config", return_value=mock_config):
        with patch("gramax_sync.mcp.tools.workspace_list_repositories", return_value=mock_repos):
            with patch("gramax_sync.mcp.tools.ensure_workspace_structure"):
                from gramax_sync.mcp.tools import clone_repositories as clone_func
                
                func = get_wrapped_function(clone_func)
                
                result = func()
                
                assert "⏭️" in result or "пропущено" in result.lower()


def test_pull_repositories_success(mock_config, mock_repositories):
    """Проверка успешного обновления репозиториев."""
    # Мокируем Path объекты
    mock_repo_path = MagicMock(spec=Path)
    mock_repo_path.exists.return_value = True
    mock_git_path = MagicMock(spec=Path)
    mock_git_path.exists.return_value = True
    mock_repo_path.__truediv__.return_value = mock_git_path
    
    mock_repos = [("section1", "catalog1", mock_repo_path)]
    
    with patch("gramax_sync.mcp.tools.require_mcp_config", return_value=mock_config):
        with patch("gramax_sync.mcp.tools.workspace_list_repositories", return_value=mock_repos):
            with patch("gramax_sync.mcp.tools.get_git_status", return_value="clean"):
                with patch("gramax_sync.mcp.tools.pull_repository"):
                    from gramax_sync.mcp.tools import pull_repositories as pull_func
                    
                    func = get_wrapped_function(pull_func)
                    
                    result = func()
                    
                    assert "🔄 Обновление репозиториев" in result
                    assert "✅" in result


def test_pull_repositories_modified(mock_config, mock_repositories):
    """Проверка пропуска репозиториев с незакоммиченными изменениями."""
    # Мокируем Path объекты
    mock_repo_path = MagicMock(spec=Path)
    mock_repo_path.exists.return_value = True
    mock_git_path = MagicMock(spec=Path)
    mock_git_path.exists.return_value = True
    mock_repo_path.__truediv__.return_value = mock_git_path
    
    mock_repos = [("section1", "catalog1", mock_repo_path)]
    
    with patch("gramax_sync.mcp.tools.require_mcp_config", return_value=mock_config):
        with patch("gramax_sync.mcp.tools.workspace_list_repositories", return_value=mock_repos):
            with patch("gramax_sync.mcp.tools.get_git_status", return_value="modified"):
                from gramax_sync.mcp.tools import pull_repositories as pull_func
                
                func = get_wrapped_function(pull_func)
                
                result = func()
                
                assert "⏭️" in result or "пропущено" in result.lower()


def test_commit_changes_success(mock_config, mock_repositories):
    """Проверка успешного коммита изменений."""
    # Мокируем Path объекты
    mock_repo_path = MagicMock(spec=Path)
    mock_repo_path.exists.return_value = True
    mock_git_path = MagicMock(spec=Path)
    mock_git_path.exists.return_value = True
    mock_repo_path.__truediv__.return_value = mock_git_path
    
    mock_repos = [("section1", "catalog1", mock_repo_path)]
    
    with patch("gramax_sync.mcp.tools.require_mcp_config", return_value=mock_config):
        with patch("gramax_sync.mcp.tools.workspace_list_repositories", return_value=mock_repos):
            with patch("gramax_sync.mcp.tools.get_git_status", return_value="modified"):
                with patch("gramax_sync.mcp.tools.commit_repository", return_value="abc1234"):
                    from gramax_sync.mcp.tools import commit_changes as commit_func
                    
                    func = get_wrapped_function(commit_func)
                    
                    result = func()
                    
                    assert "📝 Коммит изменений" in result
                    assert "✅" in result
                    assert "abc1234" in result


def test_commit_changes_no_changes(mock_config, mock_repositories):
    """Проверка пропуска репозиториев без изменений."""
    # Мокируем Path объекты
    mock_repo_path = MagicMock(spec=Path)
    mock_repo_path.exists.return_value = True
    mock_git_path = MagicMock(spec=Path)
    mock_git_path.exists.return_value = True
    mock_repo_path.__truediv__.return_value = mock_git_path
    
    mock_repos = [("section1", "catalog1", mock_repo_path)]
    
    with patch("gramax_sync.mcp.tools.require_mcp_config", return_value=mock_config):
        with patch("gramax_sync.mcp.tools.workspace_list_repositories", return_value=mock_repos):
            with patch("gramax_sync.mcp.tools.get_git_status", return_value="clean"):
                from gramax_sync.mcp.tools import commit_changes as commit_func
                
                func = get_wrapped_function(commit_func)
                
                result = func()
                
                assert "⏭️" in result or "пропущено" in result.lower()


def test_push_changes_success(mock_config, mock_repositories):
    """Проверка успешной отправки изменений."""
    # Мокируем Path объекты
    mock_repo_path = MagicMock(spec=Path)
    mock_repo_path.exists.return_value = True
    mock_git_path = MagicMock(spec=Path)
    mock_git_path.exists.return_value = True
    mock_repo_path.__truediv__.return_value = mock_git_path
    
    mock_repos = [("section1", "catalog1", mock_repo_path)]
    
    with patch("gramax_sync.mcp.tools.require_mcp_config", return_value=mock_config):
        with patch("gramax_sync.mcp.tools.workspace_list_repositories", return_value=mock_repos):
            with patch("gramax_sync.mcp.tools.get_git_status", return_value="ahead"):
                with patch("gramax_sync.mcp.tools.push_repository", return_value=2):
                    from gramax_sync.mcp.tools import push_changes as push_func
                    
                    func = get_wrapped_function(push_func)
                    
                    result = func()
                    
                    assert "🚀 Отправка изменений" in result
                    assert "✅" in result
                    assert "2 коммитов" in result


def test_push_changes_no_commits(mock_config, mock_repositories):
    """Проверка пропуска репозиториев без unpushed коммитов."""
    # Мокируем Path объекты
    mock_repo_path = MagicMock(spec=Path)
    mock_repo_path.exists.return_value = True
    mock_git_path = MagicMock(spec=Path)
    mock_git_path.exists.return_value = True
    mock_repo_path.__truediv__.return_value = mock_git_path
    
    mock_repos = [("section1", "catalog1", mock_repo_path)]
    
    with patch("gramax_sync.mcp.tools.require_mcp_config", return_value=mock_config):
        with patch("gramax_sync.mcp.tools.workspace_list_repositories", return_value=mock_repos):
            with patch("gramax_sync.mcp.tools.get_git_status", return_value="clean"):
                from gramax_sync.mcp.tools import push_changes as push_func
                
                func = get_wrapped_function(push_func)
                
                result = func()
                
                assert "⏭️" in result or "пропущено" in result.lower()


def test_sync_repositories_success(mock_config, mock_repositories):
    """Проверка успешной синхронизации репозиториев."""
    # Мокируем Path объекты
    mock_repo_path = MagicMock(spec=Path)
    mock_repo_path.exists.return_value = True
    mock_git_path = MagicMock(spec=Path)
    mock_git_path.exists.return_value = True
    mock_repo_path.__truediv__.return_value = mock_git_path
    
    mock_repos = [("section1", "catalog1", mock_repo_path)]
    
    with patch("gramax_sync.mcp.tools.require_mcp_config", return_value=mock_config):
        with patch("gramax_sync.mcp.tools.workspace_list_repositories", return_value=mock_repos):
            with patch("gramax_sync.mcp.tools.get_git_status", side_effect=["behind", "modified", "ahead"]):
                with patch("gramax_sync.mcp.tools.pull_repository"):
                        with patch("gramax_sync.git.operations.commit_repository", return_value="abc1234"):
                            with patch("gramax_sync.git.operations.push_repository", return_value=1):
                                from gramax_sync.mcp.tools import sync_repositories as sync_func
                                
                                func = get_wrapped_function(sync_func)
                                
                                result = func()
                                
                                assert "🔄 Синхронизация репозиториев" in result
                                assert "✅" in result
                                assert "📊 Итоги синхронизации" in result
