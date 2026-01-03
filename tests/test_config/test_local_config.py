"""Тесты для LocalConfig."""

import yaml

import pytest

from gramax_sync.config.local_config import LocalConfig
from gramax_sync.config.models import Catalog, Section, Source


@pytest.fixture
def sample_config_data():
    """Пример данных для LocalConfig."""
    return {
        "repo_url": "https://gitlab.example.com/ritm-authors/gramax-yaml-manager",
        "config_branch": "main",
        "catalog_branch": "private",
        "base_url": "https://gitlab.example.com",
        "workspace_dir": "~/ritm-workspace",
        "sections": [],
    }


@pytest.fixture
def sample_config_with_sections():
    """LocalConfig с секциями."""
    source = Source(url="https://gitlab.example.com")
    catalog1 = Catalog(name="catalog1", source=source)
    catalog2 = Catalog(name="catalog2", source=source)
    section1 = Section(name="section1", catalogs=[catalog1])
    section2 = Section(name="section2", catalogs=[catalog2])

    return LocalConfig(
        repo_url="https://gitlab.example.com/ritm-authors/gramax-yaml-manager",
        config_branch="main",
        catalog_branch="private",
        base_url="https://gitlab.example.com",
        workspace_dir="~/ritm-workspace",
        sections=[section1, section2],
    )


def test_local_config_creation(sample_config_data):
    """Тест создания LocalConfig."""
    config = LocalConfig(**sample_config_data)
    assert config.repo_url == sample_config_data["repo_url"]
    assert config.config_branch == "main"
    assert config.catalog_branch == "private"
    assert config.base_url == sample_config_data["base_url"]
    assert config.workspace_dir == sample_config_data["workspace_dir"]
    assert len(config.sections) == 0


def test_local_config_defaults():
    """Тест значений по умолчанию."""
    config = LocalConfig(
        repo_url="https://gitlab.example.com/repo",
        base_url="https://gitlab.example.com",
        workspace_dir="~/workspace",
    )
    assert config.config_branch == "main"
    assert config.catalog_branch == "private"
    assert len(config.sections) == 0


def test_model_dump_yaml(sample_config_with_sections):
    """Тест экспорта в YAML."""
    yaml_content = sample_config_with_sections.model_dump_yaml()
    assert isinstance(yaml_content, str)
    assert "repo_url" in yaml_content
    assert "sections" in yaml_content
    # Проверяем, что это валидный YAML
    parsed = yaml.safe_load(yaml_content)
    assert parsed["repo_url"] == sample_config_with_sections.repo_url


def test_from_yaml_string(sample_config_with_sections):
    """Тест создания из YAML строки."""
    yaml_content = sample_config_with_sections.model_dump_yaml()
    config = LocalConfig.from_yaml_string(yaml_content)
    assert config.repo_url == sample_config_with_sections.repo_url
    assert len(config.sections) == 2
    assert config.sections[0].name == "section1"


def test_from_yaml_string_empty():
    """Тест создания из пустой YAML строки."""
    with pytest.raises(ValueError, match="YAML конфигурация пуста"):
        LocalConfig.from_yaml_string("")


def test_from_yaml_string_invalid():
    """Тест создания из невалидной YAML строки."""
    with pytest.raises(Exception):  # Может быть ValueError или ValidationError
        LocalConfig.from_yaml_string("invalid: yaml: content: [unclosed")


def test_add_section(sample_config_data):
    """Тест добавления секции."""
    config = LocalConfig(**sample_config_data)
    section = Section(name="new-section", catalogs=[])
    config.add_section(section)
    assert len(config.sections) == 1
    assert config.sections[0].name == "new-section"


def test_add_section_duplicate(sample_config_with_sections):
    """Тест добавления дублирующейся секции."""
    section = Section(name="section1", catalogs=[])
    with pytest.raises(ValueError, match="уже существует"):
        sample_config_with_sections.add_section(section)


def test_remove_section(sample_config_with_sections):
    """Тест удаления секции."""
    result = sample_config_with_sections.remove_section("section1")
    assert result is True
    assert len(sample_config_with_sections.sections) == 1
    assert sample_config_with_sections.sections[0].name == "section2"


def test_remove_section_not_found(sample_config_with_sections):
    """Тест удаления несуществующей секции."""
    result = sample_config_with_sections.remove_section("nonexistent")
    assert result is False
    assert len(sample_config_with_sections.sections) == 2


def test_add_catalog(sample_config_with_sections):
    """Тест добавления каталога."""
    source = Source(url="https://gitlab.example.com")
    new_catalog = Catalog(name="catalog3", source=source)
    result = sample_config_with_sections.add_catalog("section1", new_catalog)
    assert result is True
    section = sample_config_with_sections.get_section("section1")
    assert section is not None
    assert len(section.catalogs) == 2
    assert section.catalogs[1].name == "catalog3"


def test_add_catalog_duplicate(sample_config_with_sections):
    """Тест добавления дублирующегося каталога."""
    source = Source(url="https://gitlab.example.com")
    duplicate_catalog = Catalog(name="catalog1", source=source)
    with pytest.raises(ValueError, match="уже существует"):
        sample_config_with_sections.add_catalog("section1", duplicate_catalog)


def test_add_catalog_section_not_found(sample_config_with_sections):
    """Тест добавления каталога в несуществующую секцию."""
    source = Source(url="https://gitlab.example.com")
    catalog = Catalog(name="catalog3", source=source)
    result = sample_config_with_sections.add_catalog("nonexistent", catalog)
    assert result is False


def test_remove_catalog(sample_config_with_sections):
    """Тест удаления каталога."""
    result = sample_config_with_sections.remove_catalog("section1", "catalog1")
    assert result is True
    section = sample_config_with_sections.get_section("section1")
    assert section is not None
    assert len(section.catalogs) == 0


def test_remove_catalog_not_found(sample_config_with_sections):
    """Тест удаления несуществующего каталога."""
    result = sample_config_with_sections.remove_catalog("section1", "nonexistent")
    assert result is False


def test_remove_catalog_section_not_found(sample_config_with_sections):
    """Тест удаления каталога из несуществующей секции."""
    result = sample_config_with_sections.remove_catalog("nonexistent", "catalog1")
    assert result is False


def test_get_section(sample_config_with_sections):
    """Тест получения секции."""
    section = sample_config_with_sections.get_section("section1")
    assert section is not None
    assert section.name == "section1"
    assert len(section.catalogs) == 1


def test_get_section_not_found(sample_config_with_sections):
    """Тест получения несуществующей секции."""
    section = sample_config_with_sections.get_section("nonexistent")
    assert section is None


def test_get_catalog(sample_config_with_sections):
    """Тест получения каталога."""
    catalog = sample_config_with_sections.get_catalog("section1", "catalog1")
    assert catalog is not None
    assert catalog.name == "catalog1"


def test_get_catalog_not_found(sample_config_with_sections):
    """Тест получения несуществующего каталога."""
    catalog = sample_config_with_sections.get_catalog("section1", "nonexistent")
    assert catalog is None


def test_get_catalog_section_not_found(sample_config_with_sections):
    """Тест получения каталога из несуществующей секции."""
    catalog = sample_config_with_sections.get_catalog("nonexistent", "catalog1")
    assert catalog is None

