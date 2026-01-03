"""Тесты для CLI команды auth."""

import os
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from gramax_sync.cli.auth import auth
from gramax_sync import cli

# ОБЯЗАТЕЛЬНО: Application ID должен быть установлен через переменную окружения
TEST_OAUTH_APPLICATION_ID = os.getenv("GRAMAX_OAUTH_APPLICATION_ID")
if not TEST_OAUTH_APPLICATION_ID:
    pytest.skip(
        "GRAMAX_OAUTH_APPLICATION_ID не установлен. "
        "Установите переменную окружения: export GRAMAX_OAUTH_APPLICATION_ID='ваш_id'",
        allow_module_level=True
    )


class TestAuthLogin:
    """Тесты для команды auth login."""

    @patch("gramax_sync.auth.token_manager.TokenManager.authenticate_via_oauth")
    @patch("rich.prompt.Prompt.ask")
    def test_auth_login_oauth(self, mock_prompt, mock_oauth):
        """Тест auth login --oauth."""
        mock_oauth.return_value = "test_token"
        mock_prompt.return_value = "https://gitlab.example.com"

        runner = CliRunner()
        result = runner.invoke(auth, ["login", "--oauth", "--url", "https://gitlab.example.com"])

        assert result.exit_code == 0
        mock_oauth.assert_called_once()

    @patch("gramax_sync.auth.token_manager.TokenManager.prompt_for_token")
    @patch("gramax_sync.auth.token_manager.TokenManager.save_token_with_type")
    @patch("rich.prompt.Prompt.ask")
    def test_auth_login_pat(self, mock_prompt, mock_save, mock_prompt_token):
        """Тест auth login --pat."""
        mock_prompt.return_value = "https://gitlab.example.com"
        mock_prompt_token.return_value = "test_token"

        runner = CliRunner()
        result = runner.invoke(auth, ["login", "--pat", "--url", "https://gitlab.example.com"])

        assert result.exit_code == 0
        mock_prompt_token.assert_called_once()
        mock_save.assert_called_once()

    @patch("gramax_sync.auth.token_manager.TokenManager.get_token")
    @patch("gramax_sync.auth.token_manager.TokenManager.get_token_type")
    def test_auth_status(self, mock_get_type, mock_get_token):
        """Тест auth status."""
        mock_get_token.return_value = "test_token"
        mock_get_type.return_value = "OAuth"

        runner = CliRunner()
        result = runner.invoke(auth, ["status", "--url", "https://gitlab.example.com"])

        assert result.exit_code == 0
        assert "OAuth" in result.output or "настроен" in result.output

    @patch("gramax_sync.auth.token_manager.TokenManager.get_token")
    def test_auth_status_no_token(self, mock_get_token):
        """Тест auth status без токена."""
        mock_get_token.return_value = None

        runner = CliRunner()
        result = runner.invoke(auth, ["status", "--url", "https://gitlab.example.com"])

        assert result.exit_code == 0
        assert "не настроен" in result.output or "не найден" in result.output

    @patch("gramax_sync.auth.token_manager.TokenManager.delete_token")
    @patch("gramax_sync.auth.token_manager.TokenManager.get_token")
    def test_auth_logout(self, mock_get_token, mock_delete):
        """Тест auth logout."""
        mock_get_token.return_value = "test_token"

        runner = CliRunner()
        result = runner.invoke(
            auth, ["logout", "--url", "https://gitlab.example.com", "--yes"]
        )

        assert result.exit_code == 0
        mock_delete.assert_called_once()

    @patch("gramax_sync.auth.token_manager.TokenManager.get_token")
    def test_auth_logout_no_token(self, mock_get_token):
        """Тест auth logout без токена."""
        mock_get_token.return_value = None

        runner = CliRunner()
        result = runner.invoke(auth, ["logout", "--url", "https://gitlab.example.com", "--yes"])

        assert result.exit_code == 0
        assert "не найден" in result.output


class TestAuthIntegration:
    """Интеграционные тесты для команды auth."""

    @patch("gramax_sync.auth.token_manager.TokenManager.get_token")
    @patch("gramax_sync.auth.token_manager.TokenManager.get_token_type")
    @patch("gramax_sync.auth.token_manager.TokenManager.check_token_validity")
    def test_auth_status_with_check(self, mock_check, mock_get_type, mock_get_token):
        """Тест auth status с проверкой валидности."""
        mock_get_token.return_value = "test_token"
        mock_get_type.return_value = "OAuth"
        mock_check.return_value = (True, None)

        runner = CliRunner()
        result = runner.invoke(
            auth, ["status", "--url", "https://gitlab.example.com", "--check-validity"]
        )

        assert result.exit_code == 0
        mock_check.assert_called_once()

    @patch("gramax_sync.auth.token_manager.TokenManager.get_token")
    @patch("gramax_sync.auth.token_manager.TokenManager.refresh_token")
    def test_auth_refresh_oauth(self, mock_refresh, mock_get_token):
        """Тест auth refresh через OAuth."""
        mock_get_token.return_value = "old_token"
        mock_refresh.return_value = "new_token"

        runner = CliRunner()
        result = runner.invoke(
            auth,
            [
                "refresh",
                "--url",
                "https://gitlab.example.com",
                "--oauth",
                "--application-id",
                TEST_OAUTH_APPLICATION_ID,
            ],
        )

        assert result.exit_code == 0
        mock_refresh.assert_called_once()

    @patch("gramax_sync.auth.token_manager.TokenManager.get_token")
    @patch("gramax_sync.auth.token_manager.TokenManager.refresh_token")
    def test_auth_refresh_pat(self, mock_refresh, mock_get_token):
        """Тест auth refresh через PAT."""
        mock_get_token.return_value = "old_token"
        mock_refresh.return_value = "new_token"

        runner = CliRunner()
        result = runner.invoke(
            auth, ["refresh", "--url", "https://gitlab.example.com", "--pat"]
        )

        assert result.exit_code == 0
        mock_refresh.assert_called_once()

    @patch("gramax_sync.auth.token_manager.TokenManager.get_token")
    def test_auth_refresh_no_token(self, mock_get_token):
        """Тест auth refresh без существующего токена."""
        mock_get_token.return_value = None

        runner = CliRunner()
        result = runner.invoke(
            auth, ["refresh", "--url", "https://gitlab.example.com"]
        )

        assert result.exit_code == 0
        assert "не найден" in result.output

    def test_auth_group_registered(self):
        """Тест, что команда auth зарегистрирована в CLI."""
        runner = CliRunner()
        result = runner.invoke(cli, ["auth", "--help"])

        assert result.exit_code == 0
        assert "Управление аутентификацией" in result.output

    def test_auth_login_help(self):
        """Тест справки для auth login."""
        runner = CliRunner()
        result = runner.invoke(auth, ["login", "--help"])

        assert result.exit_code == 0
        assert "Войти в систему" in result.output or "login" in result.output

    def test_auth_refresh_help(self):
        """Тест справки для auth refresh."""
        runner = CliRunner()
        result = runner.invoke(auth, ["refresh", "--help"])

        assert result.exit_code == 0
        assert "Обновить токен" in result.output or "refresh" in result.output

