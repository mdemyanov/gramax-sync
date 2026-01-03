"""Тесты для GitLab клиента."""

import base64
from unittest.mock import MagicMock, patch

import pytest
import gitlab.exceptions

from gramax_sync.gitlab.client import GitLabClient
from gramax_sync.gitlab.exceptions import (
    GitLabAuthError,
    GitLabError,
    GitLabNotFoundError,
    GitLabPermissionError,
)


@pytest.fixture
def gitlab_client():
    """Фикстура для создания GitLab клиента."""
    return GitLabClient("https://gitlab.example.com", "test-token")


@pytest.fixture
def gitlab_client_no_token():
    """Фикстура для создания GitLab клиента без токена."""
    return GitLabClient("https://gitlab.example.com")


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_gitlab_client_init_with_token(mock_gitlab_class, gitlab_client):
    """Тест инициализации клиента с токеном."""
    assert gitlab_client.url == "https://gitlab.example.com"
    assert gitlab_client.token == "test-token"
    assert gitlab_client._gl is None


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_gitlab_client_init_without_token(mock_gitlab_class, gitlab_client_no_token):
    """Тест инициализации клиента без токена."""
    assert gitlab_client_no_token.url == "https://gitlab.example.com"
    assert gitlab_client_no_token.token is None


def test_gitlab_client_url_stripping():
    """Тест удаления слеша в конце URL."""
    client = GitLabClient("https://gitlab.example.com/", "token")
    assert client.url == "https://gitlab.example.com"


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_get_client_with_token(mock_gitlab_class, gitlab_client):
    """Тест получения клиента с токеном."""
    mock_gl = MagicMock()
    mock_gitlab_class.return_value = mock_gl
    
    client = gitlab_client._get_client()
    
    assert client == mock_gl
    mock_gitlab_class.assert_called_once_with(url="https://gitlab.example.com", private_token="test-token")


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_get_client_without_token(mock_gitlab_class, gitlab_client_no_token):
    """Тест получения клиента без токена."""
    mock_gl = MagicMock()
    mock_gitlab_class.return_value = mock_gl
    
    client = gitlab_client_no_token._get_client()
    
    assert client == mock_gl
    mock_gitlab_class.assert_called_once_with(url="https://gitlab.example.com")


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_get_client_cached(mock_gitlab_class, gitlab_client):
    """Тест кэширования клиента."""
    mock_gl = MagicMock()
    mock_gitlab_class.return_value = mock_gl
    
    client1 = gitlab_client._get_client()
    client2 = gitlab_client._get_client()
    
    assert client1 == client2 == mock_gl
    assert mock_gitlab_class.call_count == 1


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_check_access_success(mock_gitlab_class, gitlab_client):
    """Тест успешной проверки доступа."""
    mock_gl = MagicMock()
    mock_gl.auth.return_value = None
    mock_gitlab_class.return_value = mock_gl
    
    result = gitlab_client.check_access()
    
    assert result is True
    mock_gl.auth.assert_called_once()


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_check_access_failure(mock_gitlab_class, gitlab_client):
    """Тест неудачной проверки доступа."""
    import gitlab.exceptions
    
    mock_gl = MagicMock()
    # Создаём реальный экземпляр исключения
    auth_error = gitlab.exceptions.GitlabAuthenticationError("Invalid token")
    mock_gl.auth.side_effect = auth_error
    mock_gitlab_class.return_value = mock_gl
    
    with pytest.raises(GitLabAuthError):
        gitlab_client.check_access()


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_get_file_content_success(mock_gitlab_class, gitlab_client):
    """Тест успешного получения содержимого файла."""
    mock_gl = MagicMock()
    mock_project = MagicMock()
    mock_file = MagicMock()
    mock_file.content = base64.b64encode(b"test content").decode()
    mock_file.encoding = "base64"
    mock_project.files.get.return_value = mock_file
    mock_gl.projects.get.return_value = mock_project
    mock_gitlab_class.return_value = mock_gl
    
    content = gitlab_client.get_file_content("project/path", "file.txt", "main")
    
    assert content == "test content"
    mock_project.files.get.assert_called_once_with(file_path="file.txt", ref="main")


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_get_file_content_not_found(mock_gitlab_class, gitlab_client):
    """Тест получения несуществующего файла."""
    mock_gl = MagicMock()
    mock_project = MagicMock()
    error_404 = gitlab.exceptions.GitlabGetError("File not found")
    error_404.response_code = 404
    mock_project.files.get.side_effect = error_404
    mock_gl.projects.get.return_value = mock_project
    mock_gitlab_class.return_value = mock_gl
    
    with pytest.raises(GitLabNotFoundError):
        gitlab_client.get_file_content("project/path", "file.txt", "main")


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_get_file_content_permission_error(mock_gitlab_class, gitlab_client):
    """Тест ошибки доступа к файлу."""
    mock_gl = MagicMock()
    mock_project = MagicMock()
    error_403 = gitlab.exceptions.GitlabGetError("Permission denied")
    error_403.response_code = 403
    mock_project.files.get.side_effect = error_403
    mock_gl.projects.get.return_value = mock_project
    mock_gitlab_class.return_value = mock_gl
    
    with pytest.raises(GitLabPermissionError):
        gitlab_client.get_file_content("project/path", "file.txt", "main")


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_get_file_content_text_encoding(mock_gitlab_class, gitlab_client):
    """Тест получения файла с текстовой кодировкой."""
    mock_gl = MagicMock()
    mock_project = MagicMock()
    mock_file = MagicMock()
    mock_file.content = "test content"
    mock_file.encoding = "text"
    mock_project.files.get.return_value = mock_file
    mock_gl.projects.get.return_value = mock_project
    mock_gitlab_class.return_value = mock_gl
    
    content = gitlab_client.get_file_content("project/path", "file.txt", "main")
    
    assert content == "test content"


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_clone_repository_url(mock_gitlab_class, gitlab_client):
    """Тест получения URL для клонирования репозитория."""
    mock_gl = MagicMock()
    mock_project = MagicMock()
    mock_project.http_url_to_repo = "https://gitlab.example.com/project/repo.git"
    mock_gl.projects.get.return_value = mock_project
    mock_gitlab_class.return_value = mock_gl
    
    url = gitlab_client.get_clone_url("project/repo")
    
    assert url == "https://gitlab.example.com/project/repo.git"


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_clone_repository_url_not_found(mock_gitlab_class, gitlab_client):
    """Тест получения URL для несуществующего репозитория."""
    mock_gl = MagicMock()
    error_404 = gitlab.exceptions.GitlabGetError("Project not found")
    error_404.response_code = 404
    mock_gl.projects.get.side_effect = error_404
    mock_gitlab_class.return_value = mock_gl
    
    with pytest.raises(GitLabNotFoundError):
        gitlab_client.get_clone_url("project/repo")


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_get_project_info_success(mock_gitlab_class, gitlab_client):
    """Тест успешного получения информации о проекте."""
    mock_gl = MagicMock()
    mock_project = MagicMock()
    mock_project.id = 123
    mock_project.name = "Test Project"
    mock_project.path_with_namespace = "group/project"
    mock_gl.projects.get.return_value = mock_project
    mock_gitlab_class.return_value = mock_gl
    
    info = gitlab_client.get_project_info("group/project")
    
    assert info["id"] == 123
    assert info["name"] == "Test Project"
    assert info["path_with_namespace"] == "group/project"


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_get_project_info_not_found(mock_gitlab_class, gitlab_client):
    """Тест получения информации о несуществующем проекте."""
    mock_gl = MagicMock()
    error_404 = gitlab.exceptions.GitlabGetError("Project not found")
    error_404.response_code = 404
    mock_gl.projects.get.side_effect = error_404
    mock_gitlab_class.return_value = mock_gl
    
    with pytest.raises(GitLabNotFoundError):
        gitlab_client.get_project_info("group/project")


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_get_project_info_generic_error(mock_gitlab_class, gitlab_client):
    """Тест обработки общей ошибки при получении информации о проекте."""
    mock_gl = MagicMock()
    mock_gl.projects.get.side_effect = Exception("Unexpected error")
    mock_gitlab_class.return_value = mock_gl
    
    with pytest.raises(GitLabError):
        gitlab_client.get_project_info("group/project")


def test_get_project_id_from_url():
    """Тест извлечения project ID из URL."""
    client = GitLabClient("https://gitlab.example.com", "token")
    
    result = client.get_project_id_from_url("https://gitlab.example.com/group/project")
    assert result == "group/project"


def test_get_project_id_from_url_with_git():
    """Тест извлечения project ID из URL с .git."""
    client = GitLabClient("https://gitlab.example.com", "token")
    
    result = client.get_project_id_from_url("https://gitlab.example.com/group/project.git")
    assert result == "group/project"


def test_get_project_id_from_url_invalid():
    """Тест обработки невалидного URL."""
    client = GitLabClient("https://gitlab.example.com", "token")
    
    with pytest.raises(ValueError):
        client.get_project_id_from_url("https://gitlab.example.com/")


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_check_repository_access_success(mock_gitlab_class, gitlab_client):
    """Тест успешной проверки доступа к репозиторию."""
    mock_gl = MagicMock()
    mock_project = MagicMock()
    # Мокируем repository_tree вместо files.get(), так как теперь используем repository_tree
    mock_project.repository_tree.return_value = [
        {"name": "workspace.yaml", "type": "blob", "path": "workspace.yaml"}
    ]
    mock_gl.projects.get.return_value = mock_project
    mock_gitlab_class.return_value = mock_gl
    
    has_access, error = gitlab_client.check_repository_access("https://gitlab.example.com/group/project")
    
    assert has_access is True
    assert error is None


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_check_repository_access_no_file(mock_gitlab_class, gitlab_client):
    """Тест проверки доступа когда файл не найден."""
    mock_gl = MagicMock()
    mock_project = MagicMock()
    error_404 = gitlab.exceptions.GitlabGetError("Not found")
    error_404.response_code = 404
    mock_project.files.get.side_effect = error_404
    mock_gl.projects.get.return_value = mock_project
    mock_gitlab_class.return_value = mock_gl
    
    has_access, error = gitlab_client.check_repository_access("https://gitlab.example.com/group/project")
    
    assert has_access is False
    assert "workspace.yaml не найден" in error


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_check_repository_access_auth_error(mock_gitlab_class, gitlab_client):
    """Тест ошибки аутентификации при проверке доступа."""
    mock_gl = MagicMock()
    mock_gl.projects.get.side_effect = gitlab.exceptions.GitlabAuthenticationError("Invalid token")
    mock_gitlab_class.return_value = mock_gl
    
    with pytest.raises(GitLabAuthError):
        gitlab_client.check_repository_access("https://gitlab.example.com/group/project")


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_check_repository_access_not_found(mock_gitlab_class, gitlab_client):
    """Тест ошибки когда репозиторий не найден."""
    mock_gl = MagicMock()
    error_404 = gitlab.exceptions.GitlabGetError("Not found")
    error_404.response_code = 404
    mock_gl.projects.get.side_effect = error_404
    mock_gitlab_class.return_value = mock_gl
    
    with pytest.raises(GitLabNotFoundError):
        gitlab_client.check_repository_access("https://gitlab.example.com/group/project")


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_check_repository_access_permission_error(mock_gitlab_class, gitlab_client):
    """Тест ошибки доступа при проверке репозитория."""
    mock_gl = MagicMock()
    error_403 = gitlab.exceptions.GitlabGetError("Forbidden")
    error_403.response_code = 403
    mock_gl.projects.get.side_effect = error_403
    mock_gitlab_class.return_value = mock_gl
    
    with pytest.raises(GitLabPermissionError):
        gitlab_client.check_repository_access("https://gitlab.example.com/group/project")


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_get_workspace_file_success(mock_gitlab_class, gitlab_client):
    """Тест успешного получения workspace.yaml."""
    mock_gl = MagicMock()
    mock_project = MagicMock()
    mock_file = MagicMock()
    mock_file.content = base64.b64encode(b"workspace: content").decode()
    mock_project.files.get.return_value = mock_file
    mock_gl.projects.get.return_value = mock_project
    mock_gitlab_class.return_value = mock_gl
    
    content = gitlab_client.get_workspace_file("https://gitlab.example.com/group/project")
    
    assert content == "workspace: content"


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_get_workspace_file_not_found(mock_gitlab_class, gitlab_client):
    """Тест получения несуществующего workspace.yaml."""
    mock_gl = MagicMock()
    mock_project = MagicMock()
    error_404 = gitlab.exceptions.GitlabGetError("Not found")
    error_404.response_code = 404
    mock_project.files.get.side_effect = error_404
    mock_gl.projects.get.return_value = mock_project
    mock_gitlab_class.return_value = mock_gl
    
    with pytest.raises(GitLabNotFoundError):
        gitlab_client.get_workspace_file("https://gitlab.example.com/group/project")


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_get_workspace_file_auth_error(mock_gitlab_class, gitlab_client):
    """Тест ошибки аутентификации при получении workspace.yaml."""
    mock_gl = MagicMock()
    mock_project = MagicMock()
    error_401 = gitlab.exceptions.GitlabGetError("Unauthorized")
    error_401.response_code = 401
    mock_project.files.get.side_effect = error_401
    mock_gl.projects.get.return_value = mock_project
    mock_gitlab_class.return_value = mock_gl
    
    with pytest.raises(GitLabAuthError):
        gitlab_client.get_workspace_file("https://gitlab.example.com/group/project")


@patch("gramax_sync.gitlab.client.gitlab.Gitlab")
def test_get_workspace_file_permission_error(mock_gitlab_class, gitlab_client):
    """Тест ошибки доступа при получении workspace.yaml."""
    mock_gl = MagicMock()
    mock_project = MagicMock()
    error_403 = gitlab.exceptions.GitlabGetError("Forbidden")
    error_403.response_code = 403
    mock_project.files.get.side_effect = error_403
    mock_gl.projects.get.return_value = mock_project
    mock_gitlab_class.return_value = mock_gl
    
    with pytest.raises(GitLabPermissionError):
        gitlab_client.get_workspace_file("https://gitlab.example.com/group/project")


def test_extract_base_url():
    """Тест извлечения базового URL."""
    client = GitLabClient("https://gitlab.example.com", "token")
    
    result = client.extract_base_url("https://gitlab.example.com/group/project")
    assert result == "https://gitlab.example.com"


def test_extract_base_url_with_port():
    """Тест извлечения базового URL с портом."""
    client = GitLabClient("https://gitlab.example.com", "token")
    
    result = client.extract_base_url("https://gitlab.example.com:8080/group/project")
    assert result == "https://gitlab.example.com:8080"

