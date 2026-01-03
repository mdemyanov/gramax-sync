"""MCP сервер для gramax-sync."""

import os
from pathlib import Path

from fastmcp import FastMCP

from gramax_sync.config.config_manager import load_config

# Создаём экземпляр MCP сервера
mcp = FastMCP("gramax-sync")


def get_mcp_config() -> Path | None:
    """Получить конфигурацию для MCP сервера.
    
    Проверяет переменные окружения и стандартное расположение конфигурации.
    
    Returns:
        Путь к конфигурационному файлу или None если не найден
    """
    # Проверяем переменную окружения GRAMAX_WORKSPACE_PATH
    workspace_path = os.getenv("GRAMAX_WORKSPACE_PATH")
    if workspace_path:
        path = Path(workspace_path)
        if path.exists():
            return path
    
    # Пробуем загрузить из стандартного места
    try:
        config = load_config()
        if config:
            # Возвращаем путь к файлу конфигурации
            from gramax_sync.config.config_manager import CONFIG_FILE
            return CONFIG_FILE
    except Exception:
        pass
    
    return None


def require_mcp_config():
    """Получить конфигурацию или выбросить ошибку.
    
    Returns:
        Объект LocalConfig
        
    Raises:
        FileNotFoundError: Если конфигурация не найдена
    """
    config = load_config()
    if config is None:
        raise FileNotFoundError(
            "Конфигурация не найдена. "
            "Установите переменную окружения GRAMAX_WORKSPACE_PATH "
            "или запустите 'gramax-sync init' для первоначальной настройки."
        )
    return config


# Импортируем инструменты для их регистрации
from gramax_sync.mcp import tools  # noqa: F401


if __name__ == "__main__":
    # Запускаем MCP сервер
    mcp.run()

