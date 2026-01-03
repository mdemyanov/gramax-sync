"""Парсер workspace.yaml."""

import yaml
from pathlib import Path

from gramax_sync.config.models import Catalog, Section, Source, Workspace, WorkspaceRaw


def _convert_raw_to_workspace(raw: WorkspaceRaw, raw_data: dict | None = None) -> Workspace:
    """Преобразовать WorkspaceRaw в Workspace для обратной совместимости.
    
    Преобразует структуру из реального формата YAML (словарь sections) 
    в формат, ожидаемый существующим кодом (список sections с объектами Catalog).
    
    Args:
        raw: Объект WorkspaceRaw с исходной структурой
        raw_data: Исходные данные YAML для извлечения дополнительных полей (например, name)
        
    Returns:
        Объект Workspace с преобразованной структурой
    """
    sections_list = []
    
    # Получаем URL источника из source или используем значение по умолчанию
    source_url = "https://itsmf.gitlab.yandexcloud.net"
    if raw.source and isinstance(raw.source, dict):
        source_url = raw.source.get("url", source_url)
    
    # Преобразуем словарь sections в список Section
    for section_id, section_raw in raw.sections.items():
        # Создаём объекты Catalog из списка строк каталогов
        catalogs = []
        for catalog_name in section_raw.catalogs:
            catalog = Catalog(
                name=catalog_name,
                source=Source(url=source_url)
            )
            catalogs.append(catalog)
        
        # Создаём Section с name из ключа словаря
        section = Section(
            name=section_id,
            catalogs=catalogs
        )
        sections_list.append(section)
    
    # Используем значение по умолчанию для workspace_dir, если оно не указано
    # Используем имя из YAML или значение по умолчанию
    workspace_name = "workspace"
    if raw_data and isinstance(raw_data, dict):
        workspace_name = raw_data.get("name", "workspace")
    workspace_dir = raw.workspace_dir or f"~/{workspace_name.lower().replace(' ', '-')}-workspace"
    
    return Workspace(
        workspace_dir=workspace_dir,
        sections=sections_list
    )


def load_workspace(path: str | Path) -> Workspace:
    """Загрузить и валидировать workspace.yaml из файла.

    Args:
        path: Путь к файлу workspace.yaml

    Returns:
        Объект Workspace с валидированными данными

    Raises:
        FileNotFoundError: Если файл не найден
        yaml.YAMLError: Если файл невалидный YAML
        ValueError: Если структура данных невалидная
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    with file_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError("Файл workspace.yaml пуст")

    # Парсим как WorkspaceRaw (реальная структура)
    raw = WorkspaceRaw.model_validate(data)
    # Преобразуем в Workspace (формат для кода)
    return _convert_raw_to_workspace(raw, data)


def load_workspace_from_string(content: str) -> Workspace:
    """Загрузить и валидировать workspace.yaml из строки.

    Args:
        content: Содержимое файла workspace.yaml

    Returns:
        Объект Workspace с валидированными данными

    Raises:
        yaml.YAMLError: Если содержимое невалидный YAML
        ValueError: Если структура данных невалидная
    """
    data = yaml.safe_load(content)

    if not data:
        raise ValueError("Содержимое workspace.yaml пусто")

    # Парсим как WorkspaceRaw (реальная структура)
    raw = WorkspaceRaw.model_validate(data)
    # Преобразуем в Workspace (формат для кода)
    return _convert_raw_to_workspace(raw, data)
