"""Pytest конфигурация и фикстуры."""

import os
import sys
from unittest.mock import MagicMock

import pytest

# URL тестового GitLab сервера для интеграционных тестов
TEST_GITLAB_URL = os.getenv("TEST_GITLAB_URL", "https://itsmf.gitlab.yandexcloud.net")

# OAuth Application ID и Secret для тестирования
# ОБЯЗАТЕЛЬНО: должны быть установлены через переменные окружения
TEST_OAUTH_APPLICATION_ID = os.getenv("GRAMAX_OAUTH_APPLICATION_ID")
TEST_OAUTH_APPLICATION_SECRET = os.getenv("GRAMAX_OAUTH_APPLICATION_SECRET")

# Проверяем, что Application ID установлен
if not TEST_OAUTH_APPLICATION_ID:
    raise ValueError(
        "GRAMAX_OAUTH_APPLICATION_ID не установлен! "
        "Установите переменную окружения перед запуском тестов: "
        "export GRAMAX_OAUTH_APPLICATION_ID='ваш_application_id'"
    )

# Мокируем keyring на уровне модуля для всех тестов
mock_keyring = MagicMock()
mock_keyring.get_password = MagicMock(return_value=None)
mock_keyring.set_password = MagicMock()
mock_keyring.delete_password = MagicMock()

sys.modules["keyring"] = mock_keyring

# Мокируем gitlab на уровне модуля для всех тестов
# Но оставляем реальные исключения для правильной работы тестов
try:
    import gitlab.exceptions
    # Используем реальные исключения, если модуль доступен
    sys.modules["gitlab.exceptions"] = gitlab.exceptions
except ImportError:
    # Если модуль недоступен, создаём мок
    mock_gitlab = MagicMock()
    mock_gitlab.Gitlab = MagicMock()
    mock_gitlab.exceptions = MagicMock()
    sys.modules["gitlab"] = mock_gitlab
    sys.modules["gitlab.exceptions"] = mock_gitlab.exceptions


@pytest.fixture
def sample_workspace_data():
    """Пример данных workspace для тестирования."""
    return {
        "workspace_dir": "/tmp/test_workspace",
        "sections": [
            {
                "name": "section1",
                "catalogs": [
                    {
                        "name": "catalog1",
                        "source": {"url": TEST_GITLAB_URL},
                    }
                ],
            }
        ],
    }


@pytest.fixture
def test_gitlab_url():
    """Фикстура для получения URL тестового GitLab сервера."""
    return TEST_GITLAB_URL


@pytest.fixture
def test_oauth_application_id():
    """Фикстура для получения OAuth Application ID."""
    return TEST_OAUTH_APPLICATION_ID


@pytest.fixture
def test_oauth_application_secret():
    """Фикстура для получения OAuth Application Secret."""
    return TEST_OAUTH_APPLICATION_SECRET
