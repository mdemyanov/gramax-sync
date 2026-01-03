"""Менеджер для работы с локальной конфигурацией."""

from pathlib import Path

from rich.console import Console

from gramax_sync.config.local_config import LocalConfig

console = Console()

# Путь к конфигурационному файлу
CONFIG_DIR = Path.home() / ".config" / "gramax-sync"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def get_config_path() -> Path:
    """Получить путь к файлу конфигурации.

    Returns:
        Путь к файлу конфигурации
    """
    return CONFIG_FILE


def get_config_dir() -> Path:
    """Получить директорию конфигурации.

    Returns:
        Путь к директории конфигурации
    """
    return CONFIG_DIR


def load_config() -> LocalConfig | None:
    """Загрузить локальную конфигурацию из файла.

    Поддерживает миграцию со старого формата JSON на YAML.

    Returns:
        Объект LocalConfig или None если файл не найден

    Raises:
        ValueError: Если конфигурация невалидная
    """
    # Проверяем наличие YAML файла
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open(encoding="utf-8") as f:
                content = f.read()
                return LocalConfig.from_yaml_string(content)
        except Exception as e:
            console.print(f"[red]Ошибка при загрузке конфигурации: {e}[/red]")
            raise

    # Проверяем наличие старого JSON файла для миграции
    old_config_file = CONFIG_DIR / "config.json"
    if old_config_file.exists():
        import json

        console.print(
            "[yellow]⚠️ Найден старый формат конфигурации (JSON). Выполняется миграция в YAML...[/yellow]"
        )
        try:
            with old_config_file.open(encoding="utf-8") as f:
                json_data = json.load(f)

            # Преобразуем JSON в LocalConfig
            from gramax_sync.config.models import Catalog, Section, Source

            sections = []
            for section_data in json_data.get("sections", []):
                catalogs = []
                for catalog_data in section_data.get("catalogs", []):
                    catalogs.append(
                        Catalog(
                            name=catalog_data["name"],
                            source=Source(url=catalog_data["source"]["url"]),
                        )
                    )
                sections.append(Section(name=section_data["name"], catalogs=catalogs))

            config = LocalConfig(
                repo_url=json_data["repo_url"],
                config_branch=json_data.get("config_branch", "master"),
                catalog_branch=json_data.get("catalog_branch", "private"),
                base_url=json_data["base_url"],
                workspace_dir=json_data["workspace_dir"],
                sections=sections,
            )

            # Сохраняем в новом формате
            save_config(config)

            # Удаляем старый файл
            old_config_file.unlink()
            console.print("[green]✅ Миграция завершена успешно[/green]")

            return config
        except Exception as e:
            console.print(f"[red]Ошибка при миграции конфигурации: {e}[/red]")
            raise

    return None


def save_config(config: LocalConfig) -> None:
    """Сохранить локальную конфигурацию в файл.

    Args:
        config: Объект LocalConfig для сохранения
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    try:
        yaml_content = config.model_dump_yaml()
        with CONFIG_FILE.open("w", encoding="utf-8") as f:
            f.write(yaml_content)
        console.print(f"[green]✓ Конфигурация сохранена: {CONFIG_FILE}[/green]")
    except Exception as e:
        console.print(f"[red]Ошибка при сохранении конфигурации: {e}[/red]")
        raise


def config_exists() -> bool:
    """Проверить существование файла конфигурации.

    Returns:
        True если файл существует, False иначе
    """
    return CONFIG_FILE.exists()


def require_config() -> LocalConfig:
    """Загрузить конфигурацию или выбросить исключение.

    Returns:
        Объект LocalConfig

    Raises:
        FileNotFoundError: Если конфигурация не найдена
    """
    config = load_config()
    if config is None:
        raise FileNotFoundError(
            f"Конфигурация не найдена. Запустите 'gramax-sync init' для первоначальной настройки."
        )
    return config

