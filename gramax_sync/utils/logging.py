"""Структурированное логирование для gramax-sync."""

import json
import logging
from typing import Any

# Настройка логирования
_logger = logging.getLogger("gramax_sync")
_logger.setLevel(logging.INFO)

# Если обработчик ещё не добавлен, создаём его
if not _logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    _logger.addHandler(handler)


class StructuredLogger:
    """Структурированный логгер для операций."""

    def __init__(self, name: str):
        """Инициализировать логгер.

        Args:
            name: Имя логгера (обычно имя модуля)
        """
        self.logger = logging.getLogger(f"gramax_sync.{name}")

    def log_operation(
        self,
        operation: str,
        level: str = "INFO",
        **kwargs: Any,
    ) -> None:
        """Логировать операцию с контекстом.

        Args:
            operation: Название операции
            level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
            **kwargs: Дополнительные поля для логирования
        """
        log_data = {
            "operation": operation,
            **kwargs,
        }

        # Фильтруем чувствительные данные
        filtered_data = self._filter_sensitive_data(log_data)

        log_message = json.dumps(filtered_data, ensure_ascii=False)

        if level == "DEBUG":
            self.logger.debug(log_message)
        elif level == "WARNING":
            self.logger.warning(log_message)
        elif level == "ERROR":
            self.logger.error(log_message)
        else:
            self.logger.info(log_message)

    def _filter_sensitive_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Отфильтровать чувствительные данные из лога.

        Args:
            data: Данные для логирования

        Returns:
            Отфильтрованные данные
        """
        sensitive_keys = {
            "token",
            "password",
            "secret",
            "api_key",
            "access_token",
            "refresh_token",
            "credentials",
        }

        filtered = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                filtered[key] = "***REDACTED***"
            elif isinstance(value, dict):
                filtered[key] = self._filter_sensitive_data(value)
            else:
                filtered[key] = value

        return filtered

    def debug(self, message: str, **kwargs: Any) -> None:
        """Логировать сообщение уровня DEBUG.

        Args:
            message: Сообщение
            **kwargs: Дополнительные поля
        """
        self.log_operation(message, level="DEBUG", **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Логировать сообщение уровня INFO.

        Args:
            message: Сообщение
            **kwargs: Дополнительные поля
        """
        self.log_operation(message, level="INFO", **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Логировать сообщение уровня WARNING.

        Args:
            message: Сообщение
            **kwargs: Дополнительные поля
        """
        self.log_operation(message, level="WARNING", **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Логировать сообщение уровня ERROR.

        Args:
            message: Сообщение
            **kwargs: Дополнительные поля
        """
        self.log_operation(message, level="ERROR", **kwargs)


def get_logger(name: str) -> StructuredLogger:
    """Получить структурированный логгер.

    Args:
        name: Имя логгера (обычно __name__)

    Returns:
        Экземпляр StructuredLogger
    """
    return StructuredLogger(name)

