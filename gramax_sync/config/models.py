"""Pydantic модели для workspace.yaml."""

from pydantic import BaseModel, Field


class Source(BaseModel):
    """Источник репозиториев (GitLab URL)."""

    url: str


class Catalog(BaseModel):
    """Каталог репозиториев."""

    name: str
    source: Source


class Section(BaseModel):
    """Секция с каталогами."""

    name: str
    catalogs: list[Catalog]


# Модели для парсинга реальной структуры YAML
class SectionRaw(BaseModel):
    """Секция в исходном формате YAML (словарь)."""

    title: str
    description: str | None = None
    icon: str | None = None
    catalogs: list[str] = Field(default_factory=list, description="Список имён каталогов")
    
    def model_post_init(self, __context) -> None:
        """Преобразовать None в пустую строку для обратной совместимости."""
        if self.description is None:
            self.description = ""
        if self.icon is None:
            self.icon = ""


class WorkspaceRaw(BaseModel):
    """Конфигурация workspace в исходном формате YAML."""

    workspace_dir: str | None = Field(default=None, description="Корневая директория для workspace")
    sections: dict[str, SectionRaw] = Field(default_factory=dict, description="Словарь секций, где ключ - идентификатор секции")
    source: dict | None = Field(default=None, description="Источник репозиториев")


class Workspace(BaseModel):
    """Конфигурация workspace (преобразованная для использования в коде)."""

    workspace_dir: str
    sections: list[Section]
