"""Тесты для TokenManager с OAuth поддержкой."""

import os
from unittest.mock import MagicMock, patch

import pytest

from gramax_sync.auth.token_manager import TokenManager

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


class TestTokenManagerOAuth:
    """Тесты для TokenManager с OAuth."""

    @patch("gramax_sync.auth.token_manager.keyring")
    def test_get_token_type(self, mock_keyring):
        """Тест получения типа токена."""
        mock_keyring.get_password.return_value = "OAuth"

        token_type = TokenManager.get_token_type(TEST_GITLAB_URL)
        assert token_type == "OAuth"

        mock_keyring.get_password.assert_called_once_with(
            "gramax-sync", f"gitlab_token_type:{TEST_GITLAB_URL}"
        )

    @patch("gramax_sync.auth.token_manager.keyring")
    def test_get_token_type_none(self, mock_keyring):
        """Тест получения типа токена, когда токен не найден."""
        mock_keyring.get_password.return_value = None

        token_type = TokenManager.get_token_type(TEST_GITLAB_URL)
        assert token_type is None

    @patch("gramax_sync.auth.token_manager.keyring")
    def test_save_token_with_type(self, mock_keyring):
        """Тест сохранения токена с типом."""
        TokenManager.save_token_with_type(
            TEST_GITLAB_URL, "test_token", "OAuth"
        )

        # Проверяем, что токен сохранён
        assert mock_keyring.set_password.call_count == 2
        calls = mock_keyring.set_password.call_args_list
        assert ("gramax-sync", f"gitlab_token:{TEST_GITLAB_URL}", "test_token") in [
            call[0] for call in calls
        ]
        assert (
            "gramax-sync",
            f"gitlab_token_type:{TEST_GITLAB_URL}",
            "OAuth",
        ) in [call[0] for call in calls]

    @patch("gramax_sync.auth.token_manager.keyring")
    @patch("gramax_sync.auth.token_manager.OAuthManager")
    @patch("os.getenv")
    def test_authenticate_via_oauth_with_param(self, mock_getenv, mock_oauth_class, mock_keyring):
        """Тест OAuth аутентификации с параметром application_id."""
        # Мокируем os.getenv чтобы не получать application_secret из окружения
        mock_getenv.side_effect = lambda key, default=None: None if key == "GRAMAX_OAUTH_APPLICATION_SECRET" else default
        
        mock_oauth_instance = MagicMock()
        mock_oauth_instance.authenticate.return_value = "test_token"
        mock_oauth_class.return_value = mock_oauth_instance

        token = TokenManager.authenticate_via_oauth(
            url=TEST_GITLAB_URL,
            application_id=TEST_OAUTH_APPLICATION_ID,
        )

        assert token == "test_token"
        mock_oauth_class.assert_called_once_with(
            base_url=TEST_GITLAB_URL,
            application_id=TEST_OAUTH_APPLICATION_ID,
            application_secret=None,
        )
        mock_oauth_instance.authenticate.assert_called_once()

    @patch("gramax_sync.auth.token_manager.keyring")
    @patch("gramax_sync.auth.token_manager.OAuthManager")
    @patch("os.getenv")
    def test_authenticate_via_oauth_from_env(self, mock_getenv, mock_oauth_class, mock_keyring):
        """Тест OAuth аутентификации с application_id из переменной окружения."""
        mock_getenv.side_effect = lambda key, default=None: {
            "GRAMAX_OAUTH_APPLICATION_ID": "env_app_id",
            "GRAMAX_OAUTH_APPLICATION_SECRET": None,
        }.get(key, default)

        mock_oauth_instance = MagicMock()
        mock_oauth_instance.authenticate.return_value = "test_token"
        mock_oauth_class.return_value = mock_oauth_instance

        token = TokenManager.authenticate_via_oauth(url=TEST_GITLAB_URL)

        assert token == "test_token"
        mock_oauth_class.assert_called_once_with(
            base_url=TEST_GITLAB_URL,
            application_id="env_app_id",
            application_secret=None,
        )

    @patch("gramax_sync.auth.token_manager.keyring")
    @patch("os.getenv")
    def test_authenticate_via_oauth_no_app_id(self, mock_getenv, mock_keyring):
        """Тест OAuth аутентификации без application_id."""
        mock_getenv.return_value = None

        with pytest.raises(ValueError, match="Не указан OAuth Application ID"):
            TokenManager.authenticate_via_oauth(url=TEST_GITLAB_URL)

    @patch("gramax_sync.auth.token_manager.GitLabClient")
    @patch("gramax_sync.auth.token_manager.keyring")
    def test_validate_token_valid(self, mock_keyring, mock_client_class):
        """Тест проверки валидности токена (валидный токен)."""
        mock_client_instance = MagicMock()
        mock_client_instance.check_access.return_value = True
        mock_client_class.return_value = mock_client_instance

        is_valid, error = TokenManager.validate_token(
            TEST_GITLAB_URL, "test_token"
        )

        assert is_valid is True
        assert error is None
        mock_client_class.assert_called_once_with(
            url=TEST_GITLAB_URL, token="test_token"
        )

    @patch("gramax_sync.auth.token_manager.GitLabClient")
    @patch("gramax_sync.auth.token_manager.keyring")
    def test_validate_token_invalid(self, mock_keyring, mock_client_class):
        """Тест проверки валидности токена (невалидный токен)."""
        from gramax_sync.gitlab.exceptions import GitLabAuthError

        mock_client_instance = MagicMock()
        mock_client_instance.check_access.side_effect = GitLabAuthError("Invalid token")
        mock_client_class.return_value = mock_client_instance

        is_valid, error = TokenManager.validate_token(
            TEST_GITLAB_URL, "invalid_token"
        )

        assert is_valid is False
        assert error is not None
        assert "невалидный" in error.lower() or "invalid" in error.lower()

    @patch("gramax_sync.auth.token_manager.TokenManager.get_token")
    @patch("gramax_sync.auth.token_manager.GitLabClient")
    def test_check_token_validity(self, mock_client_class, mock_get_token):
        """Тест проверки валидности сохранённого токена."""
        mock_get_token.return_value = "test_token"
        mock_client_instance = MagicMock()
        mock_client_instance.check_access.return_value = True
        mock_client_class.return_value = mock_client_instance

        is_valid, error = TokenManager.check_token_validity(TEST_GITLAB_URL)

        assert is_valid is True
        assert error is None
        mock_get_token.assert_called_once_with(TEST_GITLAB_URL)
        mock_client_class.assert_called_once_with(url=TEST_GITLAB_URL, token="test_token")

    @patch("gramax_sync.auth.token_manager.TokenManager.authenticate_via_oauth")
    def test_refresh_token_oauth(self, mock_oauth):
        """Тест обновления токена через OAuth."""
        mock_oauth.return_value = "new_token"

        token = TokenManager.refresh_token(
            url=TEST_GITLAB_URL,
            application_id=TEST_OAUTH_APPLICATION_ID,
            use_oauth=True,
        )

        assert token == "new_token"
        mock_oauth.assert_called_once()

    @patch("gramax_sync.auth.token_manager.TokenManager.prompt_for_token")
    @patch("gramax_sync.auth.token_manager.TokenManager.save_token_with_type")
    def test_refresh_token_pat(self, mock_save, mock_prompt):
        """Тест обновления токена через PAT."""
        mock_prompt.return_value = "new_pat_token"

        token = TokenManager.refresh_token(
            url=TEST_GITLAB_URL, use_oauth=False
        )

        assert token == "new_pat_token"
        mock_prompt.assert_called_once()
        mock_save.assert_called_once()

    @patch("gramax_sync.auth.token_manager.TokenManager.authenticate_via_oauth")
    def test_refresh_token_oauth_error(self, mock_oauth):
        """Тест обновления токена через OAuth с ошибкой."""
        mock_oauth.side_effect = Exception("OAuth error")

        with pytest.raises(ValueError, match="Не удалось обновить токен"):
            TokenManager.refresh_token(
                url=TEST_GITLAB_URL, use_oauth=True
            )

