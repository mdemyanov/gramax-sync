"""Управление токенами аутентификации."""

import keyring
from rich.console import Console
from rich.prompt import Prompt

from gramax_sync.auth.oauth import OAuthManager
from gramax_sync.gitlab.client import GitLabClient
from gramax_sync.gitlab.exceptions import GitLabAuthError, GitLabError

console = Console()

# Имя сервиса для keyring
SERVICE_NAME = "gramax-sync"
TOKEN_KEY = "gitlab_token"
TOKEN_TYPE_KEY = "gitlab_token_type"


class TokenManager:
    """Менеджер для работы с токенами аутентификации."""

    @staticmethod
    def get_token(url: str) -> str | None:
        """Получить сохранённый токен для указанного URL.

        Args:
            url: URL GitLab инстанса

        Returns:
            Токен или None если не найден
        """
        try:
            token = keyring.get_password(SERVICE_NAME, f"{TOKEN_KEY}:{url}")
            return token
        except Exception as e:
            console.print(
                f"[yellow]Предупреждение: Не удалось получить токен из keyring: {e}[/yellow]"
            )
            return None

    @staticmethod
    def save_token(url: str, token: str) -> None:
        """Сохранить токен для указанного URL.

        Args:
            url: URL GitLab инстанса
            token: Токен для сохранения
        """
        try:
            keyring.set_password(SERVICE_NAME, f"{TOKEN_KEY}:{url}", token)
            console.print("[green]✓ Токен успешно сохранён[/green]")
        except Exception as e:
            console.print(
                f"[red]Ошибка при сохранении токена: {e}[/red]"
            )
            raise

    @staticmethod
    def delete_token(url: str) -> None:
        """Удалить сохранённый токен для указанного URL.

        Args:
            url: URL GitLab инстанса
        """
        try:
            keyring.delete_password(SERVICE_NAME, f"{TOKEN_KEY}:{url}")
            console.print("[green]✓ Токен удалён[/green]")
        except Exception as e:
            console.print(
                f"[yellow]Предупреждение: Не удалось удалить токен: {e}[/yellow]"
            )

    @staticmethod
    def prompt_for_token() -> str:
        """Запросить токен у пользователя интерактивно.

        Returns:
            Введённый токен
        """
        console.print(
            "\n[cyan]Для доступа к репозиторию требуется Personal Access Token.[/cyan]"
        )
        console.print(
            "[dim]Вы можете создать токен в GitLab: Settings → Access Tokens[/dim]\n"
        )
        token = Prompt.ask(
            "Введите Personal Access Token",
            password=True,  # Скрываем ввод
        )
        return token.strip()

    @staticmethod
    def get_token_type(url: str) -> str | None:
        """Получить тип токена (PAT/OAuth).

        Args:
            url: URL GitLab инстанса

        Returns:
            Тип токена ('PAT' или 'OAuth') или None если токен не найден
        """
        try:
            token_type = keyring.get_password(SERVICE_NAME, f"{TOKEN_TYPE_KEY}:{url}")
            return token_type
        except Exception:
            return None

    @staticmethod
    def save_token_with_type(url: str, token: str, token_type: str = "PAT") -> None:
        """Сохранить токен с указанием типа.

        Args:
            url: URL GitLab инстанса
            token: Токен для сохранения
            token_type: Тип токена ('PAT' или 'OAuth')
        """
        TokenManager.save_token(url, token)
        try:
            keyring.set_password(SERVICE_NAME, f"{TOKEN_TYPE_KEY}:{url}", token_type)
        except Exception as e:
            console.print(
                f"[yellow]Предупреждение: Не удалось сохранить тип токена: {e}[/yellow]"
            )

    @staticmethod
    def authenticate_via_oauth(
        url: str,
        application_id: str | None = None,
        application_secret: str | None = None,
    ) -> str:
        """Аутентификация через OAuth flow.

        Args:
            url: URL GitLab инстанса
            application_id: ID OAuth Application (если None, берётся из переменной окружения)
            application_secret: Secret OAuth Application (опционально)

        Returns:
            Access token

        Raises:
            ValueError: Если не указан application_id и он не найден в переменных окружения
            OSError: Если не удалось запустить HTTP сервер
        """
        import os

        # Получаем application_id из параметра или переменной окружения
        if application_id is None:
            application_id = os.getenv("GRAMAX_OAUTH_APPLICATION_ID")
            if not application_id:
                raise ValueError(
                    "Не указан OAuth Application ID. "
                    "Укажите через параметр --application-id или переменную окружения GRAMAX_OAUTH_APPLICATION_ID"
                )

        # Получаем application_secret из параметра или переменной окружения
        if application_secret is None:
            application_secret = os.getenv("GRAMAX_OAUTH_APPLICATION_SECRET")

        # Создаём OAuth менеджер
        oauth_manager = OAuthManager(
            base_url=url,
            application_id=application_id,
            application_secret=application_secret,
        )

        # Выполняем OAuth flow
        token = oauth_manager.authenticate()

        # Сохраняем токен с типом
        TokenManager.save_token_with_type(url, token, "OAuth")

        return token

    @staticmethod
    def validate_token(url: str, token: str | None = None) -> tuple[bool, str | None]:
        """Проверить валидность токена через GitLab API.

        Args:
            url: URL GitLab инстанса
            token: Токен для проверки (если None, берётся из keyring)

        Returns:
            Кортеж (is_valid, error_message)
            - is_valid: True если токен валидный, False иначе
            - error_message: Сообщение об ошибке или None если токен валидный
        """
        if token is None:
            token = TokenManager.get_token(url)
            if token is None:
                return (False, "Токен не найден")

        try:
            client = GitLabClient(url=url, token=token)
            client.check_access()
            return (True, None)
        except GitLabAuthError as e:
            return (False, f"Токен невалидный: {e}")
        except GitLabError as e:
            return (False, f"Ошибка при проверке токена: {e}")
        except Exception as e:
            return (False, f"Неожиданная ошибка: {e}")

    @staticmethod
    def check_token_validity(url: str) -> tuple[bool, str | None]:
        """Проверить валидность сохранённого токена.

        Args:
            url: URL GitLab инстанса

        Returns:
            Кортеж (is_valid, error_message)
        """
        return TokenManager.validate_token(url)

    @staticmethod
    def refresh_token(
        url: str,
        application_id: str | None = None,
        application_secret: str | None = None,
        use_oauth: bool = True,
    ) -> str:
        """Обновить токен (переаутентификация).

        Args:
            url: URL GitLab инстанса
            application_id: OAuth Application ID (для OAuth)
            application_secret: OAuth Application Secret (для OAuth)
            use_oauth: Использовать OAuth для обновления (True) или PAT (False)

        Returns:
            Новый токен

        Raises:
            ValueError: Если не удалось обновить токен
        """
        if use_oauth:
            try:
                return TokenManager.authenticate_via_oauth(
                    url=url,
                    application_id=application_id,
                    application_secret=application_secret,
                )
            except Exception as e:
                raise ValueError(f"Не удалось обновить токен через OAuth: {e}") from e
        else:
            # Для PAT просто запрашиваем новый токен
            console.print("[cyan]Введите новый Personal Access Token[/cyan]")
            token = TokenManager.prompt_for_token()
            TokenManager.save_token_with_type(url, token, "PAT")
            return token

