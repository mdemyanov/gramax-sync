"""OAuth аутентификация для GitLab."""

import secrets
import socket
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable
from urllib.parse import parse_qs, quote, urlparse

from rich.console import Console

console = Console()

# Порт по умолчанию для OAuth callback
DEFAULT_OAUTH_PORT = 8765
# Timeout для ожидания callback (в секундах)
OAUTH_TIMEOUT = 300  # 5 минут


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP обработчик для OAuth callback."""

    def __init__(
        self,
        state: str,
        callback: Callable[[str, str | None], None],
        *args,
        **kwargs,
    ) -> None:
        """Инициализировать обработчик.

        Args:
            state: Ожидаемый state для проверки CSRF
            callback: Функция обратного вызова с (code, error)
        """
        self.expected_state = state
        self.callback = callback
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        """Обработать GET запрос (OAuth callback)."""
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)

        # Извлекаем code и state из query параметров
        code = query_params.get("code", [None])[0]
        state = query_params.get("state", [None])[0]
        error = query_params.get("error", [None])[0]

        # Проверяем state (CSRF защита)
        if state != self.expected_state:
            self.send_response(400)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<html><body><h1>Ошибка: Неверный state</h1></body></html>".encode("utf-8")
            )
            self.callback(None, "Неверный state")
            return

        # Отправляем ответ пользователю
        if error:
            self.send_response(400)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            error_description = query_params.get("error_description", [error])[0]
            self.wfile.write(
                f"<html><body><h1>Ошибка авторизации</h1><p>{error_description}</p></body></html>".encode(
                    "utf-8"
                )
            )
            self.callback(None, error_description)
        elif code:
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<html><body><h1>Успешно!</h1><p>Вы можете закрыть это окно.</p></body></html>".encode("utf-8")
            )
            self.callback(code, None)
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<html><body><h1>Ошибка: Не найден code</h1></body></html>".encode("utf-8")
            )
            self.callback(None, "Не найден code")

    def log_message(self, format: str, *args: object) -> None:
        """Отключить логирование HTTP сервера."""
        pass  # Не логируем запросы


def find_available_port(start_port: int = DEFAULT_OAUTH_PORT, max_attempts: int = 10) -> int:
    """Найти доступный порт.

    Args:
        start_port: Порт для начала поиска
        max_attempts: Максимальное количество попыток

    Returns:
        Доступный порт

    Raises:
        OSError: Если не удалось найти доступный порт
    """
    for i in range(max_attempts):
        port = start_port + i
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", port))
                return port
        except OSError:
            continue

    raise OSError(f"Не удалось найти доступный порт в диапазоне {start_port}-{start_port + max_attempts - 1}")


class OAuthManager:
    """Менеджер для OAuth аутентификации с GitLab."""

    def __init__(
        self,
        base_url: str,
        application_id: str,
        application_secret: str | None = None,
        redirect_port: int = DEFAULT_OAUTH_PORT,
    ) -> None:
        """Инициализировать OAuth менеджер.

        Args:
            base_url: Базовый URL GitLab инстанса
            application_id: ID OAuth Application в GitLab
            application_secret: Secret OAuth Application (опционально, для confidential apps)
            redirect_port: Порт для OAuth callback
        """
        self.base_url = base_url.rstrip("/")
        self.application_id = application_id
        self.application_secret = application_secret
        self.redirect_port = redirect_port

    def get_authorization_url(self, state: str, scopes: list[str] | None = None) -> str:
        """Получить URL для авторизации.

        Args:
            state: State для защиты от CSRF
            scopes: Список scopes (по умолчанию: read_api, read_repository, write_repository)

        Returns:
            URL для авторизации
        """
        if scopes is None:
            scopes = ["read_api", "read_repository", "write_repository"]

        redirect_uri = f"http://127.0.0.1:{self.redirect_port}/callback"
        scope_str = " ".join(scopes)

        params = {
            "client_id": self.application_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": scope_str,
        }

        query_string = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        return f"{self.base_url}/oauth/authorize?{query_string}"

    def exchange_code_for_token(self, code: str) -> str:
        """Обменять authorization code на access token.

        Args:
            code: Authorization code из callback

        Returns:
            Access token

        Raises:
            ValueError: Если не удалось получить токен
        """
        import urllib.request
        import urllib.parse

        token_url = f"{self.base_url}/oauth/token"
        redirect_uri = f"http://127.0.0.1:{self.redirect_port}/callback"

        data = {
            "client_id": self.application_id,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        # Если есть secret, добавляем его (для confidential apps)
        if self.application_secret:
            data["client_secret"] = self.application_secret

        # Отправляем POST запрос
        data_encoded = urllib.parse.urlencode(data).encode("utf-8")
        try:
            with urllib.request.urlopen(
                urllib.request.Request(token_url, data=data_encoded),
                timeout=30,
            ) as response:
                import json

                result = json.loads(response.read().decode("utf-8"))

                if "access_token" in result:
                    return result["access_token"]
                elif "error" in result:
                    error_description = result.get("error_description", result["error"])
                    raise ValueError(f"Ошибка получения токена: {error_description}")
                else:
                    raise ValueError("Неожиданный ответ от сервера")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            try:
                import json

                error_data = json.loads(error_body)
                error_description = error_data.get("error_description", error_data.get("error", str(e)))
            except Exception:
                error_description = str(e)
            raise ValueError(f"Ошибка HTTP при получении токена: {error_description}") from e
        except Exception as e:
            raise ValueError(f"Ошибка при получении токена: {e}") from e

    def authenticate(self, scopes: list[str] | None = None) -> str:
        """Выполнить полный OAuth flow для получения токена.

        Args:
            scopes: Список scopes (по умолчанию: read_api, read_repository, write_repository)

        Returns:
            Access token

        Raises:
            ValueError: Если не удалось получить токен
            OSError: Если не удалось запустить HTTP сервер
        """
        # Генерируем state для CSRF защиты
        state = secrets.token_urlsafe(32)

        # Находим доступный порт
        try:
            port = find_available_port(self.redirect_port)
            if port != self.redirect_port:
                console.print(
                    f"[yellow]⚠️  Порт {self.redirect_port} занят, используем порт {port}[/yellow]"
                )
                self.redirect_port = port
        except OSError as e:
            raise OSError(f"Не удалось найти доступный порт: {e}") from e

        # Переменные для callback
        code_received: str | None = None
        error_received: str | None = None
        callback_received = threading.Event()

        def callback(code: str | None, error: str | None) -> None:
            """Callback функция для обработки ответа."""
            nonlocal code_received, error_received
            code_received = code
            error_received = error
            callback_received.set()

        # Создаём HTTP сервер
        handler = lambda *args, **kwargs: OAuthCallbackHandler(state, callback, *args, **kwargs)
        server = HTTPServer(("127.0.0.1", self.redirect_port), handler)

        # Запускаем сервер в отдельном потоке
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        # Ждём, пока сервер запустится
        import socket
        max_wait = 5  # максимум 5 секунд
        waited = 0
        while waited < max_wait:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(("127.0.0.1", self.redirect_port))
                sock.close()
                if result == 0:
                    break  # Сервер запущен
            except Exception:
                pass
            time.sleep(0.1)
            waited += 0.1
        else:
            server.shutdown()
            server.server_close()
            raise OSError(f"Не удалось запустить HTTP сервер на порту {self.redirect_port}")

        try:
            # Генерируем authorization URL
            auth_url = self.get_authorization_url(state, scopes)

            # Открываем браузер
            console.print(f"\n[cyan]Открываю браузер для авторизации...[/cyan]")
            console.print(f"[dim]Если браузер не открылся, перейдите по ссылке:[/dim]")
            console.print(f"[dim]{auth_url}[/dim]\n")
            console.print(f"[dim]Ожидание callback на http://127.0.0.1:{self.redirect_port}/callback...[/dim]\n")

            try:
                webbrowser.open(auth_url)
            except Exception as e:
                console.print(
                    f"[yellow]⚠️  Не удалось открыть браузер автоматически: {e}[/yellow]"
                )
                console.print(f"[yellow]Пожалуйста, откройте ссылку вручную:[/yellow]")
                console.print(f"[cyan]{auth_url}[/cyan]\n")

            # Ждём callback
            console.print("[dim]Ожидание авторизации...[/dim]")
            if callback_received.wait(timeout=OAUTH_TIMEOUT):
                # Останавливаем сервер
                server.shutdown()

                if error_received:
                    raise ValueError(f"Ошибка авторизации: {error_received}")

                if code_received is None:
                    raise ValueError("Не получен authorization code")

                # Обмениваем code на token
                console.print("[dim]Получение токена...[/dim]")
                token = self.exchange_code_for_token(code_received)
                console.print("[green]✓ Токен успешно получен[/green]")
                return token
            else:
                server.shutdown()
                raise ValueError("Timeout: не получен ответ от сервера авторизации")

        except Exception as e:
            server.shutdown()
            raise
        finally:
            server.server_close()

