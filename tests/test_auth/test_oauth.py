"""Тесты для OAuth аутентификации."""

import os
import secrets
import socket
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from gramax_sync.auth.oauth import (
    DEFAULT_OAUTH_PORT,
    OAuthCallbackHandler,
    OAuthManager,
    find_available_port,
)

# URL тестового GitLab сервера
TEST_GITLAB_URL = os.getenv("TEST_GITLAB_URL", "https://itsmf.gitlab.yandexcloud.net")

# OAuth Application ID и Secret для тестирования
# ОБЯЗАТЕЛЬНО: должны быть установлены через переменные окружения
TEST_OAUTH_APPLICATION_ID = os.getenv("GRAMAX_OAUTH_APPLICATION_ID")
TEST_OAUTH_APPLICATION_SECRET = os.getenv("GRAMAX_OAUTH_APPLICATION_SECRET")

# Проверяем, что Application ID установлен
if not TEST_OAUTH_APPLICATION_ID:
    pytest.skip(
        "GRAMAX_OAUTH_APPLICATION_ID не установлен. "
        "Установите переменную окружения: export GRAMAX_OAUTH_APPLICATION_ID='ваш_id'",
        allow_module_level=True
    )


class TestFindAvailablePort:
    """Тесты для функции find_available_port."""

    def test_find_available_port_default(self):
        """Тест поиска доступного порта (по умолчанию)."""
        port = find_available_port()
        assert isinstance(port, int)
        assert port >= DEFAULT_OAUTH_PORT

    def test_find_available_port_custom_start(self):
        """Тест поиска доступного порта с кастомным начальным портом."""
        port = find_available_port(start_port=9000)
        assert isinstance(port, int)
        assert port >= 9000

    def test_find_available_port_occupied(self):
        """Тест поиска порта, когда начальный порт занят."""
        # Занимаем порт
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("localhost", DEFAULT_OAUTH_PORT))
            # Ищем доступный порт
            port = find_available_port(start_port=DEFAULT_OAUTH_PORT, max_attempts=10)
            assert port != DEFAULT_OAUTH_PORT
            assert port > DEFAULT_OAUTH_PORT


class TestOAuthCallbackHandler:
    """Тесты для OAuthCallbackHandler."""

    def test_callback_handler_success(self):
        """Тест успешного callback."""
        state = secrets.token_urlsafe(32)
        callback_called = False
        received_code = None
        received_error = None

        def callback(code: str | None, error: str | None) -> None:
            nonlocal callback_called, received_code, received_error
            callback_called = True
            received_code = code
            received_error = error

        # Создаём handler с моками для базового класса
        with patch.object(OAuthCallbackHandler, '__init__', lambda self, s, cb, *args, **kwargs: None):
            handler = OAuthCallbackHandler(state, callback, None, None, None)
            handler.expected_state = state
            handler.callback = callback
            handler.path = f"/callback?code=test_code&state={state}"
            handler.send_response = MagicMock()
            handler.send_header = MagicMock()
            handler.end_headers = MagicMock()
            handler.wfile = MagicMock()
            handler.wfile.write = MagicMock()
            
            handler.do_GET()

        assert callback_called
        assert received_code == "test_code"
        assert received_error is None

    def test_callback_handler_invalid_state(self):
        """Тест callback с неверным state."""
        state = secrets.token_urlsafe(32)
        wrong_state = "wrong_state"
        callback_called = False
        received_error = None

        def callback(code: str | None, error: str | None) -> None:
            nonlocal callback_called, received_error
            callback_called = True
            received_error = error

        # Создаём handler с моками для базового класса
        with patch.object(OAuthCallbackHandler, '__init__', lambda self, s, cb, *args, **kwargs: None):
            handler = OAuthCallbackHandler(state, callback, None, None, None)
            handler.expected_state = state
            handler.callback = callback
            handler.path = f"/callback?code=test_code&state={wrong_state}"
            handler.send_response = MagicMock()
            handler.send_header = MagicMock()
            handler.end_headers = MagicMock()
            handler.wfile = MagicMock()
            handler.wfile.write = MagicMock()
            
            handler.do_GET()

        assert callback_called
        assert received_error is not None

    def test_callback_handler_error(self):
        """Тест callback с ошибкой."""
        state = secrets.token_urlsafe(32)
        callback_called = False
        received_error = None

        def callback(code: str | None, error: str | None) -> None:
            nonlocal callback_called, received_error
            callback_called = True
            received_error = error

        # Создаём handler с моками для базового класса
        with patch.object(OAuthCallbackHandler, '__init__', lambda self, s, cb, *args, **kwargs: None):
            handler = OAuthCallbackHandler(state, callback, None, None, None)
            handler.expected_state = state
            handler.callback = callback
            handler.path = f"/callback?error=access_denied&state={state}"
            handler.send_response = MagicMock()
            handler.send_header = MagicMock()
            handler.end_headers = MagicMock()
            handler.wfile = MagicMock()
            handler.wfile.write = MagicMock()
            
            handler.do_GET()

        assert callback_called
        assert received_error is not None


class TestOAuthManager:
    """Тесты для OAuthManager."""

    def test_init(self):
        """Тест инициализации OAuthManager."""
        manager = OAuthManager(
            base_url=TEST_GITLAB_URL,
            application_id=TEST_OAUTH_APPLICATION_ID,
        )
        assert manager.base_url == TEST_GITLAB_URL
        assert manager.application_id == TEST_OAUTH_APPLICATION_ID
        assert manager.application_secret is None

    def test_init_with_secret(self):
        """Тест инициализации OAuthManager с secret."""
        manager = OAuthManager(
            base_url=TEST_GITLAB_URL,
            application_id=TEST_OAUTH_APPLICATION_ID,
            application_secret="test_secret",
        )
        assert manager.application_secret == "test_secret"

    def test_get_authorization_url(self):
        """Тест генерации authorization URL."""
        manager = OAuthManager(
            base_url=TEST_GITLAB_URL,
            application_id=TEST_OAUTH_APPLICATION_ID,
        )
        state = "test_state"
        url = manager.get_authorization_url(state)

        assert f"{TEST_GITLAB_URL}/oauth/authorize" in url
        assert f"client_id={TEST_OAUTH_APPLICATION_ID}" in url
        assert f"state={state}" in url
        assert "response_type=code" in url
        # Проверяем, что redirect_uri содержит правильный порт (используется 127.0.0.1)
        assert "redirect_uri=" in url
        assert "127.0.0.1" in url or "%3A" in url  # URL может быть закодирован
        assert "/callback" in url

    def test_get_authorization_url_custom_scopes(self):
        """Тест генерации authorization URL с кастомными scopes."""
        manager = OAuthManager(
            base_url=TEST_GITLAB_URL,
            application_id=TEST_OAUTH_APPLICATION_ID,
        )
        state = "test_state"
        scopes = ["read_api", "write_repository"]
        url = manager.get_authorization_url(state, scopes)

        assert "scope=read_api+write_repository" in url or "scope=read_api%20write_repository" in url

    @patch("urllib.request.urlopen")
    def test_exchange_code_for_token_success(self, mock_urlopen):
        """Тест обмена code на token (успешный случай)."""
        # Мокируем ответ от сервера
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"access_token": "test_token"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        manager = OAuthManager(
            base_url=TEST_GITLAB_URL,
            application_id=TEST_OAUTH_APPLICATION_ID,
        )

        token = manager.exchange_code_for_token("test_code")
        assert token == "test_token"
        # Проверяем, что был вызван urlopen
        assert mock_urlopen.called
        # Проверяем, что Request был создан с правильным URL
        call_args = mock_urlopen.call_args[0][0]
        # Request объект содержит URL, проверяем через get_full_url() или full_url
        request_url = call_args.full_url if hasattr(call_args, 'full_url') else call_args.get_full_url() if hasattr(call_args, 'get_full_url') else str(call_args)
        assert TEST_GITLAB_URL in request_url

    @patch("urllib.request.urlopen")
    def test_exchange_code_for_token_with_secret(self, mock_urlopen):
        """Тест обмена code на token с application_secret."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"access_token": "test_token"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        manager = OAuthManager(
            base_url=TEST_GITLAB_URL,
            application_id=TEST_OAUTH_APPLICATION_ID,
            application_secret="test_secret",
        )

        token = manager.exchange_code_for_token("test_code")
        assert token == "test_token"

    @patch("urllib.request.urlopen")
    def test_exchange_code_for_token_error(self, mock_urlopen):
        """Тест обмена code на token (ошибка)."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"error": "invalid_grant", "error_description": "Invalid code"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        manager = OAuthManager(
            base_url=TEST_GITLAB_URL,
            application_id=TEST_OAUTH_APPLICATION_ID,
        )

        with pytest.raises(ValueError, match="Ошибка получения токена"):
            manager.exchange_code_for_token("invalid_code")

    @patch("urllib.request.urlopen")
    def test_exchange_code_for_token_http_error(self, mock_urlopen):
        """Тест обмена code на token (HTTP ошибка)."""
        import urllib.error

        mock_error = urllib.error.HTTPError(
            url="https://gitlab.example.com/oauth/token",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=MagicMock(),
        )
        mock_error.read.return_value = b'{"error": "invalid_request"}'
        mock_urlopen.side_effect = mock_error

        manager = OAuthManager(
            base_url=TEST_GITLAB_URL,
            application_id=TEST_OAUTH_APPLICATION_ID,
        )

        with pytest.raises(ValueError, match="Ошибка HTTP"):
            manager.exchange_code_for_token("test_code")

    @patch("socket.socket")
    @patch("gramax_sync.auth.oauth.time.sleep")
    @patch("gramax_sync.auth.oauth.webbrowser")
    @patch("gramax_sync.auth.oauth.OAuthCallbackHandler")
    @patch("gramax_sync.auth.oauth.HTTPServer")
    @patch("gramax_sync.auth.oauth.find_available_port")
    @patch("gramax_sync.auth.oauth.console")
    def test_authenticate_success(self, mock_console, mock_find_port, mock_server_class, mock_handler_class, mock_webbrowser, mock_sleep, mock_socket_class):
        """Тест успешной аутентификации."""
        mock_find_port.return_value = 8765
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        
        # Мокируем socket для проверки доступности сервера
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0  # Сервер доступен
        mock_sock.settimeout = MagicMock()
        mock_sock.close = MagicMock()
        mock_socket_class.return_value = mock_sock
        
        manager = OAuthManager(
            base_url=TEST_GITLAB_URL,
            application_id=TEST_OAUTH_APPLICATION_ID,
        )
        
        # Мокируем успешный обмен кода на токен
        with patch.object(manager, "exchange_code_for_token", return_value="test_token"):
            # Перехватываем callback через handler factory
            callback_ref = {"func": None}
            
            def mock_handler_factory(state, callback, *args, **kwargs):
                """Фабрика для создания мокированного handler."""
                callback_ref["func"] = callback  # Сохраняем callback
                return MagicMock()
            
            mock_handler_class.side_effect = mock_handler_factory
            
            # Мокируем threading.Thread для сервера (чтобы сервер не запускался)
            mock_thread = MagicMock()
            
            # Мокируем threading.Event.wait чтобы вызывать callback перед возвратом True
            import threading
            
            # Мокируем wait так, чтобы он вызывал callback и возвращал True
            # Важно: используем wraps для сохранения оригинального поведения
            from functools import wraps
            
            def mock_wait(self, timeout=None):
                """Мокированный wait, который вызывает callback перед возвратом True."""
                # Вызываем callback ПЕРЕД возвратом True
                # Важно: используем сохраненный callback через замыкание
                if callback_ref["func"]:
                    # Вызываем callback - замыкание должно работать
                    callback_ref["func"]("test_code", None)
                # Устанавливаем event и возвращаем True
                self.set()
                return True
            
            with patch("gramax_sync.auth.oauth.threading.Thread", return_value=mock_thread):
                # Мокируем Event.wait через patch.object на классе threading.Event
                # Это должно работать, так как Event создается через threading.Event()
                # НО: замыкание может не работать из-за мокирования
                # Попробуем использовать реальный wait, но вызвать callback до него
                with patch.object(threading.Event, "wait", mock_wait):
                    # Вызываем authenticate
                    token = manager.authenticate()
                    
                    # Проверяем, что callback был сохранен и вызван
                    assert callback_ref["func"] is not None, "Callback должен быть сохранен"
                    
                    assert token == "test_token"
                    mock_server.shutdown.assert_called()
                    mock_webbrowser.open.assert_called()

    @patch("gramax_sync.auth.oauth.find_available_port")
    def test_authenticate_port_unavailable(self, mock_find_port):
        """Тест когда порт недоступен."""
        mock_find_port.side_effect = OSError("Port unavailable")
        
        manager = OAuthManager(
            base_url=TEST_GITLAB_URL,
            application_id=TEST_OAUTH_APPLICATION_ID,
        )
        
        with pytest.raises(OSError, match="Не удалось найти доступный порт"):
            manager.authenticate()

    @patch("socket.socket")
    @patch("gramax_sync.auth.oauth.time.sleep")
    @patch("gramax_sync.auth.oauth.webbrowser")
    @patch("gramax_sync.auth.oauth.HTTPServer")
    @patch("gramax_sync.auth.oauth.find_available_port")
    @patch("gramax_sync.auth.oauth.console")
    def test_authenticate_timeout(self, mock_console, mock_find_port, mock_server_class, mock_webbrowser, mock_sleep, mock_socket_class):
        """Тест timeout при аутентификации."""
        mock_find_port.return_value = 8765
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        
        # Мокируем socket для проверки доступности сервера
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0  # Сервер доступен
        mock_sock.settimeout = MagicMock()
        mock_sock.close = MagicMock()
        mock_socket_class.return_value = mock_sock
        
        manager = OAuthManager(
            base_url=TEST_GITLAB_URL,
            application_id=TEST_OAUTH_APPLICATION_ID,
        )
        
        # Мокируем timeout - Event.wait возвращает False
        import threading
        with patch("threading.Event.wait", return_value=False):
            with pytest.raises(ValueError, match="Timeout"):
                manager.authenticate()
            
            mock_server.shutdown.assert_called()

    @patch("socket.socket")
    @patch("gramax_sync.auth.oauth.time.sleep")
    @patch("gramax_sync.auth.oauth.webbrowser")
    @patch("gramax_sync.auth.oauth.HTTPServer")
    @patch("gramax_sync.auth.oauth.find_available_port")
    @patch("gramax_sync.auth.oauth.console")
    def test_authenticate_browser_error(self, mock_console, mock_find_port, mock_server_class, mock_webbrowser, mock_sleep, mock_socket_class):
        """Тест ошибки открытия браузера."""
        mock_find_port.return_value = 8765
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        mock_webbrowser.open.side_effect = Exception("Browser error")
        
        # Мокируем socket для проверки доступности сервера
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0  # Сервер доступен
        mock_sock.settimeout = MagicMock()
        mock_sock.close = MagicMock()
        mock_socket_class.return_value = mock_sock
        
        manager = OAuthManager(
            base_url=TEST_GITLAB_URL,
            application_id=TEST_OAUTH_APPLICATION_ID,
        )
        
        # Мокируем timeout - Event.wait возвращает False
        import threading
        with patch("threading.Event.wait", return_value=False):
            with pytest.raises(ValueError, match="Timeout"):
                manager.authenticate()
            
            # Проверяем, что было выведено сообщение об ошибке браузера
            assert any("браузер" in str(call).lower() or "browser" in str(call).lower() for call in mock_console.print.call_args_list)

    @pytest.mark.integration
    @pytest.mark.gitlab
    @pytest.mark.oauth
    def test_get_authorization_url_real_server(self):
        """Интеграционный тест: проверка генерации authorization URL для реального сервера."""
        manager = OAuthManager(
            base_url=TEST_GITLAB_URL,
            application_id=TEST_OAUTH_APPLICATION_ID,
        )
        state = "test_state"
        url = manager.get_authorization_url(state)

        # Проверяем, что URL корректно сформирован для реального сервера
        assert f"{TEST_GITLAB_URL}/oauth/authorize" in url
        assert f"client_id={TEST_OAUTH_APPLICATION_ID}" in url
        assert f"state={state}" in url
        assert "response_type=code" in url
        # URL кодируется, поэтому проверяем закодированную версию
        assert "redirect_uri=http%3A//127.0.0.1%3A8765/callback" in url

