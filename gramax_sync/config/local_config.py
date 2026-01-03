"""Модель и утилиты для локальной конфигурации."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from gramax_sync.config.models import Catalog, Section


class LocalConfig(BaseModel):
    """Локальная конфигурация gramax-sync."""

    repo_url: str = Field(description="URL репозитория с конфигурациями")
    config_branch: str = Field(default="master", description="Ветка для репозитория конфигураций")
    catalog_branch: str = Field(default="private", description="Ветка по умолчанию для каталогов")
    base_url: str = Field(description="Базовый URL GitLab")
    workspace_dir: str = Field(description="Корневая директория для workspace")
    sections: list[Section] = Field(default_factory=list, description="Список секций")

    class Config:
        """Конфигурация Pydantic."""

        json_encoders = {
            Path: str,
        }

    def model_dump_yaml(self) -> str:
        """Экспортировать конфигурацию в YAML строку.

        Returns:
            YAML строка с конфигурацией
        """
        data = self.model_dump(mode="json", exclude_none=True)
        return yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)

    @classmethod
    def from_yaml_string(cls, content: str) -> "LocalConfig":
        """Создать конфигурацию из YAML строки.

        Args:
            content: YAML строка

        Returns:
            Объект LocalConfig

        Raises:
            ValueError: Если структура данных невалидная
        """
        data = yaml.safe_load(content)
        if not data:
            raise ValueError("YAML конфигурация пуста")

        # Преобразуем sections в объекты Section
        if "sections" in data:
            sections_data = []
            for section_data in data["sections"]:
                catalogs_data = []
                for catalog_data in section_data.get("catalogs", []):
                    catalogs_data.append(
                        Catalog(
                            name=catalog_data["name"],
                            source={"url": catalog_data["source"]["url"]},
                        )
                    )
                sections_data.append(Section(name=section_data["name"], catalogs=catalogs_data))
            data["sections"] = sections_data

        return cls.model_validate(data)

    def add_section(self, section: Section) -> None:
        """Добавить секцию в конфигурацию.

        Args:
            section: Секция для добавления
        """
        # Проверяем, нет ли уже секции с таким именем
        if any(s.name == section.name for s in self.sections):
            raise ValueError(f"Секция '{section.name}' уже существует")

        self.sections.append(section)

    def remove_section(self, section_name: str) -> bool:
        """Удалить секцию из конфигурации.

        Args:
            section_name: Имя секции для удаления

        Returns:
            True если секция была удалена, False если не найдена
        """
        initial_count = len(self.sections)
        self.sections = [s for s in self.sections if s.name != section_name]
        return len(self.sections) < initial_count

    def add_catalog(self, section_name: str, catalog: Catalog) -> bool:
        """Добавить каталог в секцию.

        Args:
            section_name: Имя секции
            catalog: Каталог для добавления

        Returns:
            True если каталог был добавлен, False если секция не найдена

        Raises:
            ValueError: Если каталог с таким именем уже существует в секции
        """
        for section in self.sections:
            if section.name == section_name:
                # Проверяем, нет ли уже каталога с таким именем
                if any(c.name == catalog.name for c in section.catalogs):
                    raise ValueError(
                        f"Каталог '{catalog.name}' уже существует в секции '{section_name}'"
                    )

                section.catalogs.append(catalog)
                return True

        return False

    def remove_catalog(self, section_name: str, catalog_name: str) -> bool:
        """Удалить каталог из секции.

        Args:
            section_name: Имя секции
            catalog_name: Имя каталога для удаления

        Returns:
            True если каталог был удалён, False если не найден
        """
        for section in self.sections:
            if section.name == section_name:
                initial_count = len(section.catalogs)
                section.catalogs = [c for c in section.catalogs if c.name != catalog_name]
                return len(section.catalogs) < initial_count

        return False

    def get_section(self, section_name: str) -> Section | None:
        """Получить секцию по имени.

        Args:
            section_name: Имя секции

        Returns:
            Секция или None если не найдена
        """
        for section in self.sections:
            if section.name == section_name:
                return section
        return None

    def get_catalog(self, section_name: str, catalog_name: str) -> Catalog | None:
        """Получить каталог по имени секции и каталога.

        Args:
            section_name: Имя секции
            catalog_name: Имя каталога

        Returns:
            Каталог или None если не найден
        """
        section = self.get_section(section_name)
        if section:
            for catalog in section.catalogs:
                if catalog.name == catalog_name:
                    return catalog
        return None

