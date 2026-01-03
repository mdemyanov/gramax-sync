"""Клиент для работы с GitLab API."""

import base64
import json
from urllib.parse import urlparse

import gitlab
import gitlab.exceptions
from rich.console import Console

from gramax_sync.gitlab.exceptions import (
    GitLabAuthError,
    GitLabError,
    GitLabNotFoundError,
    GitLabPermissionError,
)

console = Console()


class GitLabClient:
    """Клиент для работы с GitLab API."""

    def __init__(self, url: str, token: str | None = None) -> None:
        """Инициализировать клиент GitLab.

        Args:
            url: URL GitLab инстанса (например, https://gitlab.example.com)
            token: Personal Access Token (опционально)
        """
        self.url = url.rstrip("/")
        self.token = token
        self._gl: gitlab.Gitlab | None = None

    def _get_client(self) -> gitlab.Gitlab:
        """Получить или создать клиент GitLab."""
        if self._gl is None:
            if self.token:
                self._gl = gitlab.Gitlab(url=self.url, private_token=self.token)
            else:
                self._gl = gitlab.Gitlab(url=self.url)
        return self._gl

    def _reset_client(self) -> None:
        """Сбросить клиент GitLab (например, после обновления токена)."""
        self._gl = None

    def check_access(self) -> bool:
        """Проверить доступ к GitLab API.

        Returns:
            True если доступ есть, False иначе

        Raises:
            GitLabAuthError: Если требуется аутентификация
            GitLabError: При других ошибках
        """
        try:
            gl = self._get_client()
            gl.auth()  # Проверяем аутентификацию
            return True
        except gitlab.exceptions.GitlabAuthenticationError as e:
            error_msg = f"Требуется аутентификация: {e}"
            # Добавляем полезное сообщение для пользователя
            if "401" in str(e) or "Unauthorized" in str(e):
                error_msg += "\n💡 Запустите 'gramax-sync auth login' для аутентификации"
            raise GitLabAuthError(error_msg) from e
        except Exception as e:
            raise GitLabError(f"Ошибка при проверке доступа: {e}") from e

    def get_project_id_from_url(self, repo_url: str) -> str:
        """Извлечь project ID или path из URL репозитория.

        Args:
            repo_url: URL репозитория (например, https://gitlab.com/group/project)

        Returns:
            Путь к проекту в формате group/project

        Raises:
            ValueError: Если URL невалидный
        """
        parsed = urlparse(repo_url)
        path = parsed.path.strip("/")

        if not path:
            raise ValueError(f"Невалидный URL репозитория: {repo_url}")

        # Убираем .git если есть
        if path.endswith(".git"):
            path = path[:-4]

        return path

    def check_repository_access(
        self, repo_url: str, branch: str = "private"
    ) -> tuple[bool, str | None]:
        """Проверить доступ к репозиторию и наличие файла workspace.yaml.

        Args:
            repo_url: URL репозитория
            branch: Ветка для проверки (по умолчанию: private)

        Returns:
            Кортеж (доступ_есть, ошибка_или_None)

        Raises:
            GitLabAuthError: Если требуется аутентификация
            GitLabPermissionError: Если нет доступа
            GitLabNotFoundError: Если репозиторий не найден
        """
        try:
            gl = self._get_client()
            project_path = self.get_project_id_from_url(repo_url)

            # Проверяем, что токен установлен
            if not self.token:
                console.print(f"[dim]DEBUG: Токен не установлен в GitLabClient[/dim]")
                raise GitLabAuthError(
                    f"Требуется аутентификация для доступа к репозиторию: {repo_url}\n"
                    "💡 Запустите 'gramax-sync auth login' для аутентификации"
                )

            # Получаем проект
            # Обрабатываем случай, когда projects.get() возвращает Response вместо RESTObject
            project = None
            try:
                project = gl.projects.get(project_path)
            except gitlab.exceptions.GitlabAuthenticationError as e:
                raise GitLabAuthError(
                    f"Требуется аутентификация для доступа к репозиторию: {e}"
                ) from e
            except gitlab.exceptions.GitlabGetError as e:
                if e.response_code == 404:
                    raise GitLabNotFoundError(
                        f"Репозиторий не найден: {repo_url}"
                    ) from e
                elif e.response_code == 401:
                    raise GitLabAuthError(
                        f"Требуется аутентификация для доступа к репозиторию: {repo_url}\n"
                        "💡 Запустите 'gramax-sync auth login' для аутентификации"
                    ) from e
                elif e.response_code == 403:
                    raise GitLabPermissionError(
                        f"Нет доступа к репозиторию: {repo_url}\n"
                        "💡 Проверьте права токена или запустите 'gramax-sync auth refresh' для обновления"
                    ) from e
                raise GitLabError(f"Ошибка при доступе к репозиторию: {e}") from e
            except gitlab.exceptions.GitlabParsingError as e:
                # Если python-gitlab не может распарсить ответ, пробуем через projects.list()
                console.print(f"[dim]DEBUG: GitlabParsingError при projects.get(): {e}[/dim]")
                try:
                    projects = [p for p in gl.projects.list(get_all=True) 
                               if p.path_with_namespace == project_path]
                    if projects:
                        project = projects[0]
                    else:
                        raise GitLabNotFoundError(f"Репозиторий не найден: {repo_url}")
                except Exception as list_error:
                    console.print(f"[dim]DEBUG: Ошибка при получении списка проектов: {list_error}[/dim]")
                    raise GitLabError(f"Ошибка при доступе к репозиторию: {e}") from e
            except (TypeError, ValueError, AttributeError, Exception) as e:
                # Для любых других ошибок пробуем через projects.list()
                console.print(f"[dim]DEBUG: Неожиданная ошибка при projects.get(): {type(e).__name__}: {e}[/dim]")
                try:
                    projects = [p for p in gl.projects.list(get_all=True) 
                               if p.path_with_namespace == project_path]
                    if projects:
                        project = projects[0]
                    else:
                        raise GitLabNotFoundError(f"Репозиторий не найден: {repo_url}")
                except Exception as list_error:
                    console.print(f"[dim]DEBUG: Ошибка при получении списка проектов: {list_error}[/dim]")
                    raise GitLabError(f"Ошибка при доступе к репозиторию: {e}") from e
            
            # Проверяем наличие workspace.yaml
            if project is None:
                raise GitLabNotFoundError(f"Репозиторий не найден: {repo_url}")

            # Проверяем наличие файла workspace.yaml
            # Используем прямой HTTP запрос для получения всех элементов дерева (без ограничения пагинации)
            try:
                import requests
                encoded_path = project_path.replace('/', '%2F')
                headers = {"PRIVATE-TOKEN": self.token} if self.token else {}
                all_items = []
                page = 1
                per_page = 100
                
                # Получаем все элементы дерева с пагинацией
                while True:
                    tree_response = requests.get(
                        f"{self.url}/api/v4/projects/{encoded_path}/repository/tree",
                        headers=headers,
                        params={"path": "", "ref": branch, "recursive": "true", "per_page": per_page, "page": page},
                        timeout=30
                    )
                    if tree_response.status_code != 200:
                        break
                    items = tree_response.json()
                    if not items:
                        break
                    all_items.extend(items)
                    # Если получили меньше элементов, чем запросили, значит это последняя страница
                    if len(items) < per_page:
                        break
                    page += 1
                
                # Ищем workspace.yaml в дереве репозитория
                file_found = any(
                    item.get('name') == 'workspace.yaml' and item.get('type') == 'blob'
                    for item in all_items
                    if isinstance(item, dict)
                )
                if file_found:
                    return (True, None)
                return (
                    False,
                    f"Файл workspace.yaml не найден в ветке '{branch}'",
                )
            except (TypeError, ValueError, AttributeError, gitlab.exceptions.GitlabParsingError) as tree_error:
                # Обрабатываем случай, когда repository_tree возвращает Response вместо списка или ошибку парсинга
                error_str = str(tree_error).lower()
                if "restobject" in error_str or "response" in error_str or "non-dictionary" in error_str or "parsing" in error_str:
                    # Пробуем использовать прямой HTTP запрос для получения дерева через requests
                    try:
                        encoded_path = project_path.replace('/', '%2F')
                        console.print(f"[dim]DEBUG: Попытка получить дерево через прямой HTTP: /projects/{encoded_path}/repository/tree[/dim]")
                        import requests
                        headers = {"PRIVATE-TOKEN": self.token} if self.token else {}
                        tree_response = requests.get(
                            f"{self.url}/api/v4/projects/{encoded_path}/repository/tree",
                            headers=headers,
                            params={"path": "", "ref": branch, "recursive": "true"},
                            timeout=30
                        )
                        console.print(f"[dim]DEBUG: Прямой запрос дерева: статус={tree_response.status_code}[/dim]")
                        
                        if tree_response.status_code == 200:
                            try:
                                response = tree_response.json()
                            except json.JSONDecodeError as json_error:
                                console.print(f"[dim]DEBUG: Ошибка парсинга JSON дерева: {json_error}[/dim]")
                                raise GitLabError(f"Не удалось распарсить дерево репозитория: {json_error}") from json_error
                        elif tree_response.status_code == 404:
                            return (
                                False,
                                f"Файл workspace.yaml не найден в ветке '{branch}'",
                            )
                        elif tree_response.status_code == 401:
                            raise GitLabAuthError(
                                f"Требуется аутентификация для доступа к репозиторию: {repo_url}\n"
                                "💡 Запустите 'gramax-sync auth login' для аутентификации"
                            )
                        elif tree_response.status_code == 403:
                            raise GitLabPermissionError(
                                f"Нет доступа к репозиторию: {repo_url}\n"
                                "💡 Проверьте права токена или запустите 'gramax-sync auth refresh' для обновления"
                            )
                        else:
                            raise GitLabError(f"Ошибка при получении дерева репозитория: HTTP {tree_response.status_code}")
                        
                        if response and isinstance(response, list):
                            file_found = any(
                                item.get('name') == 'workspace.yaml' and item.get('type') == 'blob'
                                for item in response
                                if isinstance(item, dict)
                            )
                            if file_found:
                                return (True, None)
                            return (
                                False,
                                f"Файл workspace.yaml не найден в ветке '{branch}'",
                            )
                        else:
                            return (
                                False,
                                f"Файл workspace.yaml не найден в ветке '{branch}'",
                            )
                    except (GitLabAuthError, GitLabPermissionError, GitLabNotFoundError):
                        raise
                    except Exception as http_error:
                        console.print(f"[dim]DEBUG: Ошибка при получении дерева через альтернативный метод: {http_error}[/dim]")
                        raise GitLabError(f"Ошибка при проверке файла через альтернативный метод: {http_error}") from http_error
                else:
                    raise GitLabError(f"Ошибка при проверке файла: {tree_error}") from tree_error
            except gitlab.exceptions.GitlabGetError as tree_error:
                if tree_error.response_code == 404:
                    return (
                        False,
                        f"Файл workspace.yaml не найден в ветке '{branch}'",
                    )
                elif tree_error.response_code == 401:
                    raise GitLabAuthError(
                        f"Требуется аутентификация для доступа к репозиторию: {repo_url}\n"
                        "💡 Запустите 'gramax-sync auth login' для аутентификации"
                    ) from tree_error
                elif tree_error.response_code == 403:
                    raise GitLabPermissionError(
                        f"Нет доступа к репозиторию: {repo_url}\n"
                        "💡 Проверьте права токена или запустите 'gramax-sync auth refresh' для обновления"
                    ) from tree_error
                raise GitLabError(f"Ошибка при проверке файла: {tree_error}") from tree_error
            except Exception as e:
                # Обрабатываем другие исключения
                if isinstance(e, (GitLabAuthError, GitLabPermissionError, GitLabNotFoundError)):
                    raise
                raise GitLabError(f"Неожиданная ошибка при проверке файла: {e}") from e

        except (GitLabAuthError, GitLabPermissionError, GitLabNotFoundError):
            raise
        except Exception as e:
            raise GitLabError(f"Неожиданная ошибка: {e}") from e

    def get_workspace_file(self, repo_url: str, branch: str = "private") -> str:
        """Получить содержимое файла workspace.yaml из репозитория.

        Args:
            repo_url: URL репозитория
            branch: Ветка (по умолчанию: private)

        Returns:
            Содержимое файла workspace.yaml

        Raises:
            GitLabAuthError: Если требуется аутентификация
            GitLabPermissionError: Если нет доступа
            GitLabNotFoundError: Если файл не найден
        """
        try:
            gl = self._get_client()
            project_path = self.get_project_id_from_url(repo_url)
            
            # Получаем проект с обработкой ошибок парсинга
            try:
                project = gl.projects.get(project_path)
            except (TypeError, ValueError, AttributeError, gitlab.exceptions.GitlabParsingError) as e:
                error_str = str(e).lower()
                if "restobject" in error_str or "response" in error_str or "parsing" in error_str:
                    # Используем прямой HTTP запрос
                    import requests
                    encoded_path = project_path.replace('/', '%2F')
                    headers = {"PRIVATE-TOKEN": self.token} if self.token else {}
                    proj_response = requests.get(
                        f"{self.url}/api/v4/projects/{encoded_path}",
                        headers=headers,
                        timeout=10
                    )
                    if proj_response.status_code == 200:
                        project_data = proj_response.json()
                        project_id = project_data.get('id')
                        if project_id:
                            project = gl.projects.get(project_id)
                        else:
                            raise GitLabNotFoundError(f"Репозиторий не найден: {repo_url}")
                    elif proj_response.status_code == 404:
                        raise GitLabNotFoundError(f"Репозиторий не найден: {repo_url}")
                    elif proj_response.status_code == 401:
                        raise GitLabAuthError(
                            f"Требуется аутентификация для доступа к репозиторию: {repo_url}\n"
                            "💡 Запустите 'gramax-sync auth login' для аутентификации"
                        )
                    elif proj_response.status_code == 403:
                        raise GitLabPermissionError(
                            f"Нет доступа к репозиторию: {repo_url}\n"
                            "💡 Проверьте права токена или запустите 'gramax-sync auth refresh' для обновления"
                        )
                    else:
                        raise GitLabError(f"Ошибка при получении проекта: HTTP {proj_response.status_code}")
                else:
                    raise

            # Получаем файл с обработкой ошибок парсинга
            try:
                file_content = project.files.get(file_path="workspace.yaml", ref=branch)
                # Декодируем содержимое файла
                content = base64.b64decode(file_content.content).decode("utf-8")
                return content
            except (TypeError, ValueError, AttributeError, gitlab.exceptions.GitlabParsingError) as file_error:
                error_str = str(file_error).lower()
                if "restobject" in error_str or "response" in error_str or "parsing" in error_str:
                    # Используем прямой HTTP запрос для получения файла
                    import requests
                    encoded_path = project_path.replace('/', '%2F')
                    headers = {"PRIVATE-TOKEN": self.token} if self.token else {}
                    file_response = requests.get(
                        f"{self.url}/api/v4/projects/{encoded_path}/repository/files/workspace.yaml",
                        headers=headers,
                        params={"ref": branch},
                        timeout=10
                    )
                    if file_response.status_code == 200:
                        file_data = file_response.json()
                        content_b64 = file_data.get('content', '')
                        content = base64.b64decode(content_b64).decode("utf-8")
                        return content
                    elif file_response.status_code == 404:
                        raise GitLabNotFoundError(f"Файл workspace.yaml не найден в ветке '{branch}'")
                    elif file_response.status_code == 401:
                        raise GitLabAuthError(
                            f"Требуется аутентификация для доступа к файлу workspace.yaml\n"
                            "💡 Запустите 'gramax-sync auth login' для аутентификации"
                        )
                    elif file_response.status_code == 403:
                        raise GitLabPermissionError(
                            f"Нет доступа к файлу workspace.yaml\n"
                            "💡 Проверьте права токена или запустите 'gramax-sync auth refresh' для обновления"
                        )
                    else:
                        raise GitLabError(f"Ошибка при получении файла: HTTP {file_response.status_code}")
                else:
                    raise

        except gitlab.exceptions.GitlabAuthenticationError as e:
            raise GitLabAuthError(
                f"Требуется аутентификация: {e}"
            ) from e
        except gitlab.exceptions.GitlabGetError as e:
            if e.response_code == 404:
                raise GitLabNotFoundError(
                    f"Файл workspace.yaml не найден в ветке '{branch}'"
                ) from e
            elif e.response_code == 401:
                raise GitLabAuthError(
                    f"Требуется аутентификация для доступа к файлу workspace.yaml\n"
                    "💡 Запустите 'gramax-sync auth login' для аутентификации"
                ) from e
            elif e.response_code == 403:
                raise GitLabPermissionError(
                    f"Нет доступа к файлу workspace.yaml\n"
                    "💡 Проверьте права токена или запустите 'gramax-sync auth refresh' для обновления"
                ) from e
            raise GitLabError(f"Ошибка при получении файла: {e}") from e
        except Exception as e:
            raise GitLabError(f"Неожиданная ошибка: {e}") from e

    def extract_base_url(self, repo_url: str) -> str:
        """Извлечь базовый URL GitLab из URL репозитория.

        Args:
            repo_url: Полный URL репозитория

        Returns:
            Базовый URL (например, https://gitlab.example.com)
        """
        parsed = urlparse(repo_url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def get_file_content(
        self, project_path: str, file_path: str, branch: str = "master"
    ) -> str:
        """Получить содержимое файла из репозитория.

        Args:
            project_path: Путь к проекту (например, group/project)
            file_path: Путь к файлу в репозитории
            branch: Ветка (по умолчанию: master)

        Returns:
            Содержимое файла как строка

        Raises:
            GitLabAuthError: Если требуется аутентификация
            GitLabPermissionError: Если нет доступа
            GitLabNotFoundError: Если файл не найден
            GitLabError: При других ошибках
        """
        try:
            gl = self._get_client()
            
            # Получаем проект с обработкой ошибок парсинга
            try:
                project = gl.projects.get(project_path)
            except (TypeError, ValueError, AttributeError, gitlab.exceptions.GitlabParsingError) as e:
                error_str = str(e).lower()
                if "restobject" in error_str or "response" in error_str or "parsing" in error_str:
                    import requests
                    encoded_path = project_path.replace('/', '%2F')
                    headers = {"PRIVATE-TOKEN": self.token} if self.token else {}
                    proj_response = requests.get(
                        f"{self.url}/api/v4/projects/{encoded_path}",
                        headers=headers,
                        timeout=10
                    )
                    if proj_response.status_code == 200:
                        project_data = proj_response.json()
                        project_id = project_data.get('id')
                        if project_id:
                            project = gl.projects.get(project_id)
                        else:
                            raise GitLabNotFoundError(f"Проект {project_path} не найден")
                    elif proj_response.status_code == 404:
                        raise GitLabNotFoundError(f"Проект {project_path} не найден")
                    elif proj_response.status_code == 401:
                        raise GitLabAuthError(
                            f"Требуется аутентификация для доступа к проекту: {project_path}\n"
                            "💡 Запустите 'gramax-sync auth login' для аутентификации"
                        )
                    elif proj_response.status_code == 403:
                        raise GitLabPermissionError(
                            f"Нет доступа к проекту: {project_path}\n"
                            "💡 Проверьте права токена или запустите 'gramax-sync auth refresh' для обновления"
                        )
                    else:
                        raise GitLabError(f"Ошибка при получении проекта: HTTP {proj_response.status_code}")
                else:
                    raise
            
            # Получаем файл с обработкой ошибок парсинга
            try:
                file_obj = project.files.get(file_path=file_path, ref=branch)
            except (TypeError, ValueError, AttributeError, gitlab.exceptions.GitlabParsingError) as file_error:
                error_str = str(file_error).lower()
                if "restobject" in error_str or "response" in error_str or "parsing" in error_str:
                    # Используем прямой HTTP запрос для получения файла
                    import requests
                    encoded_path = project_path.replace('/', '%2F')
                    encoded_file_path = file_path.replace('/', '%2F')
                    headers = {"PRIVATE-TOKEN": self.token} if self.token else {}
                    file_response = requests.get(
                        f"{self.url}/api/v4/projects/{encoded_path}/repository/files/{encoded_file_path}",
                        headers=headers,
                        params={"ref": branch},
                        timeout=10
                    )
                    if file_response.status_code == 200:
                        file_data = file_response.json()
                        encoding = file_data.get('encoding', 'base64')
                        content_b64 = file_data.get('content', '')
                        if encoding == "base64":
                            content = base64.b64decode(content_b64).decode("utf-8")
                        else:
                            content = content_b64
                        return content
                    elif file_response.status_code == 404:
                        raise GitLabNotFoundError(f"Файл {file_path} не найден в ветке '{branch}'")
                    elif file_response.status_code == 401:
                        raise GitLabAuthError(
                            f"Требуется аутентификация для доступа к файлу {file_path}\n"
                            "💡 Запустите 'gramax-sync auth login' для аутентификации"
                        )
                    elif file_response.status_code == 403:
                        raise GitLabPermissionError(
                            f"Нет доступа к файлу {file_path}\n"
                            "💡 Проверьте права токена или запустите 'gramax-sync auth refresh' для обновления"
                        )
                    else:
                        raise GitLabError(f"Ошибка при получении файла: HTTP {file_response.status_code}")
                else:
                    raise

            # Декодируем содержимое в зависимости от кодировки
            if file_obj.encoding == "base64":
                content = base64.b64decode(file_obj.content).decode("utf-8")
            elif file_obj.encoding == "text":
                content = file_obj.content
            else:
                # По умолчанию пытаемся декодировать как base64
                try:
                    content = base64.b64decode(file_obj.content).decode("utf-8")
                except Exception:
                    # Если не получается, используем как есть
                    content = file_obj.content

            return content

        except gitlab.exceptions.GitlabAuthenticationError as e:
            raise GitLabAuthError(
                f"Требуется аутентификация для доступа к файлу: {e}"
            ) from e
        except gitlab.exceptions.GitlabGetError as e:
            if e.response_code == 404:
                raise GitLabNotFoundError(
                    f"Файл {file_path} не найден в ветке '{branch}'"
                ) from e
            elif e.response_code == 401:
                raise GitLabAuthError(
                    f"Требуется аутентификация для доступа к файлу {file_path}\n"
                    "💡 Запустите 'gramax-sync auth login' для аутентификации"
                ) from e
            elif e.response_code == 403:
                raise GitLabPermissionError(
                    f"Нет доступа к файлу {file_path}\n"
                    "💡 Проверьте права токена или запустите 'gramax-sync auth refresh' для обновления"
                ) from e
            raise GitLabError(f"Ошибка при получении файла: {e}") from e
        except Exception as e:
            raise GitLabError(f"Неожиданная ошибка при получении файла: {e}") from e

    def get_clone_url(self, project_path: str) -> str:
        """Получить URL для клонирования репозитория.

        Args:
            project_path: Путь к проекту (например, group/project)

        Returns:
            HTTP URL для клонирования репозитория

        Raises:
            GitLabAuthError: Если требуется аутентификация
            GitLabNotFoundError: Если проект не найден
            GitLabError: При других ошибках
        """
        try:
            gl = self._get_client()
            
            # Получаем проект с обработкой ошибок парсинга
            try:
                project = gl.projects.get(project_path)
            except (TypeError, ValueError, AttributeError, gitlab.exceptions.GitlabParsingError) as e:
                error_str = str(e).lower()
                if "restobject" in error_str or "response" in error_str or "parsing" in error_str:
                    import requests
                    encoded_path = project_path.replace('/', '%2F')
                    headers = {"PRIVATE-TOKEN": self.token} if self.token else {}
                    proj_response = requests.get(
                        f"{self.url}/api/v4/projects/{encoded_path}",
                        headers=headers,
                        timeout=10
                    )
                    if proj_response.status_code == 200:
                        project_data = proj_response.json()
                        project_id = project_data.get('id')
                        if project_id:
                            project = gl.projects.get(project_id)
                        else:
                            raise GitLabNotFoundError(f"Проект {project_path} не найден")
                    elif proj_response.status_code == 404:
                        raise GitLabNotFoundError(f"Проект {project_path} не найден")
                    elif proj_response.status_code == 401:
                        raise GitLabAuthError(
                            f"Требуется аутентификация для доступа к проекту: {project_path}\n"
                            "💡 Запустите 'gramax-sync auth login' для аутентификации"
                        )
                    elif proj_response.status_code == 403:
                        raise GitLabPermissionError(
                            f"Нет доступа к проекту: {project_path}\n"
                            "💡 Проверьте права токена или запустите 'gramax-sync auth refresh' для обновления"
                        )
                    else:
                        raise GitLabError(f"Ошибка при получении проекта: HTTP {proj_response.status_code}")
                else:
                    raise
            
            return project.http_url_to_repo

        except gitlab.exceptions.GitlabAuthenticationError as e:
            raise GitLabAuthError(
                f"Требуется аутентификация для доступа к проекту: {e}"
            ) from e
        except gitlab.exceptions.GitlabGetError as e:
            if e.response_code == 404:
                raise GitLabNotFoundError(
                    f"Проект {project_path} не найден"
                ) from e
            raise GitLabError(f"Ошибка при получении URL клонирования: {e}") from e
        except Exception as e:
            raise GitLabError(
                f"Неожиданная ошибка при получении URL клонирования: {e}"
            ) from e

    def get_project_info(self, project_path: str) -> dict[str, int | str]:
        """Получить информацию о проекте.

        Args:
            project_path: Путь к проекту (например, group/project)

        Returns:
            Словарь с информацией о проекте (id, name, path_with_namespace)

        Raises:
            GitLabAuthError: Если требуется аутентификация
            GitLabNotFoundError: Если проект не найден
            GitLabError: При других ошибках
        """
        try:
            gl = self._get_client()
            
            # Получаем проект с обработкой ошибок парсинга
            try:
                project = gl.projects.get(project_path)
            except (TypeError, ValueError, AttributeError, gitlab.exceptions.GitlabParsingError) as e:
                error_str = str(e).lower()
                if "restobject" in error_str or "response" in error_str or "parsing" in error_str:
                    import requests
                    encoded_path = project_path.replace('/', '%2F')
                    headers = {"PRIVATE-TOKEN": self.token} if self.token else {}
                    proj_response = requests.get(
                        f"{self.url}/api/v4/projects/{encoded_path}",
                        headers=headers,
                        timeout=10
                    )
                    if proj_response.status_code == 200:
                        project_data = proj_response.json()
                        return {
                            "id": project_data.get('id'),
                            "name": project_data.get('name', ''),
                            "path_with_namespace": project_data.get('path_with_namespace', project_path),
                        }
                    elif proj_response.status_code == 404:
                        raise GitLabNotFoundError(f"Проект {project_path} не найден")
                    elif proj_response.status_code == 401:
                        raise GitLabAuthError(
                            f"Требуется аутентификация для доступа к проекту: {project_path}\n"
                            "💡 Запустите 'gramax-sync auth login' для аутентификации"
                        )
                    elif proj_response.status_code == 403:
                        raise GitLabPermissionError(
                            f"Нет доступа к проекту: {project_path}\n"
                            "💡 Проверьте права токена или запустите 'gramax-sync auth refresh' для обновления"
                        )
                    else:
                        raise GitLabError(f"Ошибка при получении проекта: HTTP {proj_response.status_code}")
                else:
                    raise
            
            return {
                "id": project.id,
                "name": project.name,
                "path_with_namespace": project.path_with_namespace,
            }

        except gitlab.exceptions.GitlabAuthenticationError as e:
            raise GitLabAuthError(
                f"Требуется аутентификация для доступа к проекту: {e}"
            ) from e
        except gitlab.exceptions.GitlabGetError as e:
            if e.response_code == 404:
                raise GitLabNotFoundError(
                    f"Проект {project_path} не найден"
                ) from e
            raise GitLabError(f"Ошибка при получении информации о проекте: {e}") from e
        except Exception as e:
            raise GitLabError(
                f"Неожиданная ошибка при получении информации о проекте: {e}"
            ) from e

