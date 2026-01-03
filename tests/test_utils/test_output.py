"""Тесты для утилит вывода."""

from gramax_sync.utils.output import console


def test_console_initialized():
    """Проверка инициализации console."""
    assert console is not None
    assert hasattr(console, 'print')

